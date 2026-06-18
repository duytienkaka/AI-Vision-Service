import os
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path

import httpx
import numpy as np
from PIL import Image
from sqlalchemy.orm import Session

from app import crud, schemas
from app.core.config import settings
from app.core.logging import get_logger

os.environ.setdefault("YOLO_CONFIG_DIR", settings.yolo_config_dir)
os.environ.setdefault("TORCH_HOME", settings.torch_home)

from ultralytics import YOLO

logger = get_logger(__name__)

_MODEL: YOLO | None = None
_COCO_TO_DOMAIN = {
    "person": "PERSON",
}


class ImageTooLargeError(ValueError):
    pass


class ObjectStorageReferenceError(ValueError):
    pass


def _load_model() -> YOLO:
    global _MODEL
    if _MODEL is None:
        logger.info("Loading YOLO model %s", settings.yolo_model_name)
        _MODEL = YOLO(settings.yolo_model_name)
    return _MODEL


def _fetch_image(source: schemas.ImageUrlSource) -> Image.Image:
    response = httpx.get(
        str(source.url),
        timeout=settings.image_fetch_timeout_seconds,
        follow_redirects=True,
    )
    response.raise_for_status()
    return _load_image_from_bytes(response.content)


def _load_image_from_bytes(content: bytes) -> Image.Image:
    if len(content) > settings.max_image_size_bytes:
        raise ImageTooLargeError(
            f"Image exceeds maxImageSizeBytes limit ({settings.max_image_size_bytes} bytes)"
        )
    return Image.open(BytesIO(content)).convert("RGB")


def _resolve_storage_path(source: schemas.ObjectStorageSource) -> Path:
    if source.expiresAt < datetime.now(timezone.utc):
        raise ObjectStorageReferenceError("OBJECT_STORAGE_REF has expired")

    root = Path(settings.object_storage_root).resolve()
    target = (root / source.bucket / source.objectKey).resolve()

    if root not in target.parents and target != root:
        raise ObjectStorageReferenceError("OBJECT_STORAGE_REF points outside the configured storage root")

    if not target.is_file():
        raise ObjectStorageReferenceError("OBJECT_STORAGE_REF does not exist in the configured storage root")

    return target


def _fetch_object_storage_image(source: schemas.ObjectStorageSource) -> Image.Image:
    target = _resolve_storage_path(source)
    return _load_image_from_bytes(target.read_bytes())


def save_uploaded_image(filename: str, content: bytes) -> Path:
    uploads_dir = Path(settings.uploads_dir)
    uploads_dir.mkdir(parents=True, exist_ok=True)
    safe_name = Path(filename).name or "upload.jpg"
    target = uploads_dir / safe_name

    if target.exists():
        target = uploads_dir / f"{target.stem}-{datetime.now(timezone.utc):%Y%m%d%H%M%S}{target.suffix}"

    target.write_bytes(content)
    return target


def save_identity_reference_image(person_code: str, filename: str, content: bytes) -> Path:
    identity_dir = Path(settings.identity_gallery_dir)
    identity_dir.mkdir(parents=True, exist_ok=True)
    safe_name = Path(filename).name or "identity.jpg"
    extension = Path(safe_name).suffix or ".jpg"
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S%f")
    target = identity_dir / f"{person_code.lower()}-{timestamp}{extension}"
    target.write_bytes(content)
    return target


def _build_objects(result) -> list[schemas.DetectedObject]:
    objects: list[schemas.DetectedObject] = []
    if result.boxes is None or result.orig_shape is None:
        return objects

    image_height, image_width = result.orig_shape
    names = result.names

    for index, box in enumerate(result.boxes):
        class_id = int(box.cls[0].item())
        label = names.get(class_id, "unknown")
        domain_label = _COCO_TO_DOMAIN.get(label.lower(), "UNKNOWN")
        confidence = float(box.conf[0].item())
        x1, y1, x2, y2 = box.xyxy[0].tolist()

        objects.append(
            schemas.DetectedObject(
                objectType=domain_label,
                label=label,
                confidence=confidence,
                trackId=f"TRACK-{index + 1}",
                boundingBox=schemas.BoundingBox(
                    x=max(0.0, min(1.0, x1 / image_width)),
                    y=max(0.0, min(1.0, y1 / image_height)),
                    width=max(0.0, min(1.0, (x2 - x1) / image_width)),
                    height=max(0.0, min(1.0, (y2 - y1) / image_height)),
                ),
            )
        )
    return objects


def _extract_feature_vector(image: Image.Image) -> np.ndarray:
    resized = image.resize((48, 96)).convert("RGB")
    array = np.asarray(resized, dtype=np.float32) / 255.0
    means = array.mean(axis=(0, 1))
    stds = array.std(axis=(0, 1))

    hist_parts: list[np.ndarray] = []
    for channel in range(3):
        hist, _ = np.histogram(array[:, :, channel], bins=8, range=(0.0, 1.0), density=True)
        hist_parts.append(hist.astype(np.float32))

    thumbnail = array[::4, ::4, :].reshape(-1)
    vector = np.concatenate([means, stds, *hist_parts, thumbnail]).astype(np.float32)
    norm = np.linalg.norm(vector)
    return vector if norm == 0 else vector / norm


def _cosine_similarity(left: np.ndarray, right: np.ndarray) -> float:
    return float(np.dot(left, right))


def _crop_image(image: Image.Image, bounding_box: schemas.BoundingBox) -> Image.Image:
    width, height = image.size
    x1 = int(max(0, min(width, bounding_box.x * width)))
    y1 = int(max(0, min(height, bounding_box.y * height)))
    x2 = int(max(0, min(width, (bounding_box.x + bounding_box.width) * width)))
    y2 = int(max(0, min(height, (bounding_box.y + bounding_box.height) * height)))
    if x2 <= x1 or y2 <= y1:
        return image.crop((0, 0, 1, 1))
    return image.crop((x1, y1, x2, y2))


def _recognize_persons(
    db: Session,
    image: Image.Image,
    objects: list[schemas.DetectedObject],
) -> list[schemas.RecognizedPerson]:
    identities = crud.list_known_identities(db)
    if not identities:
        return []

    recognized: list[schemas.RecognizedPerson] = []
    for item in objects:
        if item.objectType != "PERSON":
            continue

        crop = _crop_image(image, item.boundingBox)
        feature = _extract_feature_vector(crop)
        best_name: str | None = None
        best_score = -1.0

        for identity in identities:
            gallery_feature = np.asarray(identity.embedding_vector, dtype=np.float32)
            score = _cosine_similarity(feature, gallery_feature)
            if score > best_score:
                best_score = score
                best_name = identity.display_name

        if best_name is None or best_score < settings.identity_match_threshold:
            continue

        recognized.append(
            schemas.RecognizedPerson(
                trackId=item.trackId,
                displayName=best_name.title(),
                matchConfidence=max(0.0, min(1.0, best_score)),
                detectionConfidence=item.confidence,
                boundingBox=item.boundingBox,
                objectLabel=item.label,
            )
        )

    return recognized


def _derive_risk_level(objects: list[schemas.DetectedObject]) -> str:
    if any(item.objectType == "PERSON" for item in objects):
        return "HIGH"
    if objects:
        return "MEDIUM"
    return "LOW"


def _derive_alert_hint(risk_level: str) -> str:
    if risk_level in {"HIGH", "CRITICAL"}:
        return "REVIEW_SECURITY"
    if risk_level == "MEDIUM":
        return "MONITOR"
    return "NONE"


def _predict_image(
    *,
    detection_id: str,
    request_id: str,
    trace_id: str,
    image: Image.Image,
    thumbnail_url: str | None,
) -> schemas.DetectionResult:
    now = datetime.now(timezone.utc)
    model = _load_model()
    prediction = model.predict(image, verbose=False)[0]
    objects = _build_objects(prediction)
    risk_level = _derive_risk_level(objects)
    summary = (
        f"Detected {len(objects)} object(s); top labels: "
        + ", ".join(item.label or item.objectType for item in objects[:3])
        if objects
        else "No supported objects detected in the image"
    )

    return schemas.DetectionResult(
        detectionId=detection_id,
        requestId=request_id,
        traceId=trace_id,
        status="COMPLETED",
        confidence=max((item.confidence for item in objects), default=0),
        riskLevel=risk_level,
        modelVersion=settings.yolo_model_name,
        summary=summary,
        alertHint=_derive_alert_hint(risk_level),
        processedAt=now,
        completedAt=now,
        thumbnailUrl=thumbnail_url,
        objects=objects,
        errorDetail=None,
    )


def _detect_objects(image: Image.Image) -> list[schemas.DetectedObject]:
    model = _load_model()
    prediction = model.predict(image, verbose=False)[0]
    return _build_objects(prediction)


def _select_reference_crop(image: Image.Image) -> Image.Image:
    try:
        objects = _detect_objects(image)
    except Exception:
        return image

    person_objects = [item for item in objects if item.objectType == "PERSON"]
    if not person_objects:
        return image

    largest_person = max(
        person_objects,
        key=lambda item: item.boundingBox.width * item.boundingBox.height,
    )
    return _crop_image(image, largest_person.boundingBox)


def _run_detection(
    *,
    db: Session | None,
    image: Image.Image,
    detection_id: str,
    request_id: str,
    trace_id: str,
    thumbnail_url: str | None,
) -> tuple[schemas.DetectionResult, list[schemas.RecognizedPerson]]:
    objects = _detect_objects(image)
    now = datetime.now(timezone.utc)
    risk_level = _derive_risk_level(objects)
    summary = (
        f"Detected {len(objects)} object(s); top labels: "
        + ", ".join(item.label or item.objectType for item in objects[:3])
        if objects
        else "No supported objects detected in the image"
    )
    result = schemas.DetectionResult(
        detectionId=detection_id,
        requestId=request_id,
        traceId=trace_id,
        status="COMPLETED",
        confidence=max((item.confidence for item in objects), default=0),
        riskLevel=risk_level,
        modelVersion=settings.yolo_model_name,
        summary=summary,
        alertHint=_derive_alert_hint(risk_level),
        processedAt=now,
        completedAt=now,
        thumbnailUrl=thumbnail_url,
        objects=objects,
        errorDetail=None,
    )
    recognized = _recognize_persons(db, image, result.objects) if db is not None else []
    return result, recognized


def process_detection_request(
    detection_id: str,
    payload: schemas.DetectionRequest,
) -> schemas.DetectionResult:
    now = datetime.now(timezone.utc)

    try:
        if payload.imageSource.sourceType != "IMAGE_URL":
            image = _fetch_object_storage_image(payload.imageSource)
            thumbnail_url = None
        else:
            image = _fetch_image(payload.imageSource)
            thumbnail_url = str(payload.imageSource.url)

        result, _ = _run_detection(
            db=None,
            detection_id=detection_id,
            request_id=payload.requestId,
            trace_id=payload.traceId,
            image=image,
            thumbnail_url=thumbnail_url,
        )
        return result
    except Exception as exc:
        logger.exception("YOLO detection failed for request %s", payload.requestId)
        return schemas.DetectionResult(
            detectionId=detection_id,
            requestId=payload.requestId,
            traceId=payload.traceId,
            status="FAILED",
            confidence=0,
            riskLevel="LOW",
            modelVersion=settings.yolo_model_name,
            summary="Detection failed while processing the input image",
            alertHint="NONE",
            processedAt=now,
            completedAt=now,
            thumbnailUrl=None,
            objects=[],
            errorDetail=str(exc)[:500],
        )


def process_uploaded_image(
    *,
    detection_id: str,
    request_id: str,
    trace_id: str,
    image_bytes: bytes,
    thumbnail_url: str,
) -> schemas.DetectionResult:
    try:
        image = _load_image_from_bytes(image_bytes)
        result, _ = _run_detection(
            db=None,
            detection_id=detection_id,
            request_id=request_id,
            trace_id=trace_id,
            image=image,
            thumbnail_url=thumbnail_url,
        )
        return result
    except Exception as exc:
        now = datetime.now(timezone.utc)
        logger.exception("YOLO detection failed for uploaded request %s", request_id)
        return schemas.DetectionResult(
            detectionId=detection_id,
            requestId=request_id,
            traceId=trace_id,
            status="FAILED",
            confidence=0,
            riskLevel="LOW",
            modelVersion=settings.yolo_model_name,
            summary="Detection failed while processing the uploaded image",
            alertHint="NONE",
            processedAt=now,
            completedAt=now,
            thumbnailUrl=None,
            objects=[],
            errorDetail=str(exc)[:500],
        )


def _resolve_image_from_request(payload: schemas.DetectionRequest) -> tuple[Image.Image, str | None]:
    if payload.imageSource.sourceType == "IMAGE_URL":
        return _fetch_image(payload.imageSource), str(payload.imageSource.url)
    return _fetch_object_storage_image(payload.imageSource), None


def process_identity_request(db: Session, payload: schemas.DetectionRequest) -> schemas.IdentityCheckResponse:
    now = datetime.now(timezone.utc)
    try:
        image, thumbnail_url = _resolve_image_from_request(payload)
        temporary_detection_id = f"DET-{now:%Y%m%d}-9999"
        result, recognized = _run_detection(
            db=db,
            image=image,
            detection_id=temporary_detection_id,
            request_id=payload.requestId,
            trace_id=payload.traceId,
            thumbnail_url=thumbnail_url,
        )

        if recognized:
            names = ", ".join(person.displayName for person in recognized[:3])
            summary = f"Detected {len(result.objects)} object(s); recognized person: {names}"
        else:
            summary = (
                f"Detected {len(result.objects)} object(s); no known identity matched"
                if any(item.objectType == "PERSON" for item in result.objects)
                else "No person detected for identity matching"
            )

        return schemas.IdentityCheckResponse(
            requestId=payload.requestId,
            traceId=payload.traceId,
            status="COMPLETED",
            modelVersion=result.modelVersion or settings.yolo_model_name,
            summary=summary,
            processedAt=result.processedAt or now,
            personCount=sum(1 for item in result.objects if item.objectType == "PERSON"),
            recognizedPersons=recognized,
            errorDetail=None,
        )
    except Exception as exc:
        logger.exception("Identity check failed for request %s", payload.requestId)
        return schemas.IdentityCheckResponse(
            requestId=payload.requestId,
            traceId=payload.traceId,
            status="FAILED",
            modelVersion=settings.yolo_model_name,
            summary="Identity check failed while processing the input image",
            processedAt=now,
            personCount=0,
            recognizedPersons=[],
            errorDetail=str(exc)[:500],
        )


def register_identity_reference(
    db: Session,
    *,
    person_code: str,
    display_name: str,
    notes: str | None,
    filename: str,
    content: bytes,
) -> schemas.IdentityRegisterResponse:
    image = _load_image_from_bytes(content)
    reference_crop = _select_reference_crop(image)
    embedding_vector = _extract_feature_vector(reference_crop).astype(float).tolist()
    saved_path = save_identity_reference_image(person_code, filename, content)
    crud.create_identity_reference_sample(
        db,
        person_code=person_code,
        image_path=str(saved_path),
        embedding_vector=embedding_vector,
    )
    samples = crud.list_identity_reference_samples(db, person_code)
    averaged_vector = (
        np.mean(
            [np.asarray(sample.embedding_vector, dtype=np.float32) for sample in samples],
            axis=0,
        )
        .astype(float)
        .tolist()
    )
    identity, action = crud.upsert_known_identity(
        db,
        person_code=person_code,
        display_name=display_name,
        notes=notes,
        reference_image_path=samples[0].image_path,
        embedding_vector=averaged_vector,
    )
    return schemas.IdentityRegisterResponse(
        status=action,
        identity=_build_identity_record(db, identity),
    )


def _build_identity_record(db: Session, identity) -> schemas.IdentityRecord:
    samples = crud.list_identity_reference_samples(db, identity.person_code)
    image_urls = [f"/media-identities/{Path(sample.image_path).name}" for sample in samples]
    primary_url = image_urls[0] if image_urls else f"/media-identities/{Path(identity.reference_image_path).name}"
    return schemas.IdentityRecord(
        personCode=identity.person_code,
        displayName=identity.display_name,
        notes=identity.notes,
        referenceImageUrl=primary_url,
        referenceImageUrls=image_urls,
        sampleCount=len(samples),
        createdAt=identity.created_at,
        updatedAt=identity.updated_at,
    )


def build_identity_records(db: Session) -> list[schemas.IdentityRecord]:
    return [_build_identity_record(db, item) for item in crud.list_known_identities(db)]


def delete_identity(db: Session, person_code: str) -> schemas.IdentityDeleteResponse | None:
    deleted, samples = crud.delete_known_identity(db, person_code)
    if not deleted:
        return None

    for sample in samples:
        path = Path(sample.image_path)
        if path.is_file():
            path.unlink(missing_ok=True)

    return schemas.IdentityDeleteResponse(
        status="DELETED",
        personCode=person_code,
        deletedSampleCount=len(samples),
    )
