import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, Header, HTTPException, Response, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app import crud, schemas
from app.core.auth import require_bearer_token
from app.core.config import settings
from app.db import get_db
from app.integrations.core_client import build_core_detection_notification, send_detection_to_core
from app.services.detection_service import (
    build_identity_records,
    delete_identity,
    register_identity_reference,
    process_identity_request,
    process_detection_request,
    process_uploaded_image,
    save_uploaded_image,
)

router = APIRouter()
WEB_DIR = Path(__file__).resolve().parents[1] / "web"


def _build_detection_snapshot(detection) -> schemas.DetectionSnapshot:
    return schemas.DetectionSnapshot(
        status=detection.status,
        confidence=detection.confidence,
        riskLevel=detection.risk_level,
        modelVersion=detection.model_version,
        summary=detection.summary,
        alertHint=detection.alert_hint,
        personDetected=detection.person_detected,
        knownPersonDetected=detection.known_person_detected,
        identityMatches=[
            schemas.IdentityMatch.model_validate(item) for item in (detection.identity_matches_payload or [])
        ],
        completedAt=detection.completed_at,
        thumbnailUrl=detection.thumbnail_url,
        objects=[schemas.DetectedObject.model_validate(item) for item in detection.objects_payload],
    )


def _build_detection_result(detection) -> schemas.DetectionResult:
    snapshot = _build_detection_snapshot(detection)
    return schemas.DetectionResult(
        detectionId=detection.detection_id,
        requestId=detection.request_id,
        traceId=detection.trace_id,
        status=snapshot.status,
        confidence=snapshot.confidence,
        riskLevel=snapshot.riskLevel,
        modelVersion=snapshot.modelVersion,
        summary=snapshot.summary,
        alertHint=snapshot.alertHint,
        personDetected=snapshot.personDetected,
        knownPersonDetected=snapshot.knownPersonDetected,
        identityMatches=snapshot.identityMatches,
        completedAt=snapshot.completedAt,
        thumbnailUrl=snapshot.thumbnailUrl,
        objects=snapshot.objects,
        processedAt=detection.processed_at,
        errorDetail=detection.error_detail,
    )


@router.get("/health", response_model=schemas.HealthStatus, tags=["health"])
def get_health() -> schemas.HealthStatus:
    return schemas.HealthStatus(
        status="ok",
        service="ai-vision",
        time=datetime.now(timezone.utc),
    )


@router.get("/demo", include_in_schema=False)
def get_demo_page() -> FileResponse:
    return FileResponse(WEB_DIR / "index.html")


@router.post(
    "/demo/api/detect",
    response_model=schemas.DemoDetectionResponse,
    tags=["vision"],
)
async def demo_detect_upload(
    image: UploadFile = File(...),
    cameraId: str = Form("CAM-DEMO-01"),
    zoneId: str = Form("DEMO-ZONE"),
    notes: str = Form("Demo upload from Vision UI"),
    motionLevel: float = Form(0.75),
    db: Session = Depends(get_db),
) -> schemas.DemoDetectionResponse:
    content = await image.read()
    if not content:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Uploaded image is empty")

    request_id = f"REQ-DEMO-{datetime.now(timezone.utc):%Y%m%d}-{uuid.uuid4().hex[:4].upper()}"
    trace_id = f"TRACE-DEMO-{datetime.now(timezone.utc):%Y%m%d}-{uuid.uuid4().hex[:4].upper()}"
    saved_path = save_uploaded_image(image.filename or "upload.jpg", content)
    image_url = f"/media/{saved_path.name}"

    detection = crud.create_detection_record(
        db,
        request_id=request_id,
        trace_id=trace_id,
        camera_id=cameraId,
        captured_at=datetime.now(timezone.utc),
        zone_id=zoneId,
        motion_level=motionLevel,
        notes=notes,
        image_source=schemas.UploadedImageSource(
            sourceType="UPLOADED_FILE",
            filename=image.filename or saved_path.name,
            contentType=image.content_type,
            localPath=str(saved_path),
        ).model_dump(mode="json"),
    )
    result = process_uploaded_image(
        detection_id=detection.detection_id,
        request_id=request_id,
        trace_id=trace_id,
        image_bytes=content,
        thumbnail_url=image_url,
    )
    crud.update_detection_result(db, detection.id, result)
    notification = build_core_detection_notification(
        result=result,
        camera_id=cameraId,
        captured_at=detection.captured_at,
        zone_id=zoneId,
    )
    send_detection_to_core(notification)

    return schemas.DemoDetectionResponse(
        detectionId=detection.detection_id,
        requestId=request_id,
        traceId=trace_id,
        imageUrl=image_url,
        result=result,
    )


@router.post(
    "/vision/detect",
    response_model=schemas.DetectionSubmission,
    status_code=status.HTTP_202_ACCEPTED,
    tags=["vision"],
)
def create_detection(
    payload: schemas.DetectionRequest,
    db: Session = Depends(get_db),
    _: str = Depends(require_bearer_token),
    correlation_id: Annotated[str | None, Header(alias="X-Correlation-Id")] = None,
) -> schemas.DetectionSubmission:
    del correlation_id

    existing = crud.get_detection_by_request_id(db, payload.requestId)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"requestId {payload.requestId} already exists",
        )

    detection = crud.create_detection(db, payload)
    result = process_detection_request(detection.detection_id, payload)
    processed = crud.update_detection_result(db, detection.id, result)
    notification = build_core_detection_notification(
        result=result,
        camera_id=detection.camera_id,
        captured_at=detection.captured_at,
        zone_id=detection.zone_id,
    )
    send_detection_to_core(notification)

    return schemas.DetectionSubmission(
        detectionId=detection.detection_id,
        requestId=detection.request_id,
        traceId=detection.trace_id,
        status="PROCESSING",
        acceptedAt=detection.accepted_at,
        preliminaryResult=_build_detection_snapshot(processed),
    )


@router.post(
    "/vision/identify",
    response_model=schemas.IdentityCheckResponse,
    tags=["vision"],
)
def identify_person(
    payload: schemas.DetectionRequest,
    db: Session = Depends(get_db),
    _: str = Depends(require_bearer_token),
    correlation_id: Annotated[str | None, Header(alias="X-Correlation-Id")] = None,
) -> schemas.IdentityCheckResponse:
    del correlation_id
    return process_identity_request(db, payload)


@router.post(
    "/vision/identities/register",
    response_model=schemas.IdentityRegisterResponse,
    tags=["vision"],
)
async def register_identity(
    personCode: str = Form(..., pattern=r"^ID-[A-Z0-9-]+$"),
    displayName: str = Form(..., min_length=1, max_length=120),
    notes: str | None = Form(default=None, min_length=1, max_length=300),
    image: UploadFile = File(...),
    db: Session = Depends(get_db),
    _: str = Depends(require_bearer_token),
) -> schemas.IdentityRegisterResponse:
    content = await image.read()
    if not content:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Uploaded image is empty")

    return register_identity_reference(
        db,
        person_code=personCode,
        display_name=displayName,
        notes=notes,
        filename=image.filename or f"{personCode}.jpg",
        content=content,
    )


@router.get(
    "/vision/identities",
    response_model=list[schemas.IdentityRecord],
    tags=["vision"],
)
def list_identities(
    db: Session = Depends(get_db),
    _: str = Depends(require_bearer_token),
) -> list[schemas.IdentityRecord]:
    return build_identity_records(db)


@router.delete(
    "/vision/identities/{personCode}",
    response_model=schemas.IdentityDeleteResponse,
    tags=["vision"],
)
def remove_identity(
    personCode: str,
    db: Session = Depends(get_db),
    _: str = Depends(require_bearer_token),
) -> schemas.IdentityDeleteResponse:
    deleted = delete_identity(db, personCode)
    if deleted is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"personCode {personCode} does not exist")
    return deleted


@router.get(
    "/vision/detections/{detectionId}",
    response_model=schemas.DetectionResult,
    tags=["vision"],
)
def get_detection_by_id(
    detectionId: str,
    db: Session = Depends(get_db),
    _: str = Depends(require_bearer_token),
    correlation_id: Annotated[str | None, Header(alias="X-Correlation-Id")] = None,
) -> schemas.DetectionResult:
    del correlation_id

    detection = crud.get_detection_by_detection_id(db, detectionId)
    if not detection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"detectionId {detectionId} does not exist",
        )

    return _build_detection_result(detection)


@router.get("/vision/models/info", response_model=schemas.ModelInfo, tags=["models"])
def get_model_info(
    db: Session = Depends(get_db),
    _: str = Depends(require_bearer_token),
    correlation_id: Annotated[str | None, Header(alias="X-Correlation-Id")] = None,
) -> schemas.ModelInfo:
    del db, correlation_id

    return schemas.ModelInfo(
        modelName="yolo-hospital-monitor",
        modelVersion=settings.yolo_model_name,
        supportedObjectTypes=["PERSON", "WHEELCHAIR", "STRETCHER", "SMOKE"],
        supportedImageSourceTypes=["IMAGE_URL", "OBJECT_STORAGE_REF"],
        maxImageSizeBytes=settings.max_image_size_bytes,
        notes="Pretrained YOLO model loaded locally for image URL and uploaded image inference",
        lastUpdatedAt=datetime(2026, 5, 1, tzinfo=timezone.utc),
    )


@router.get("/", include_in_schema=False)
def root() -> Response:
    return Response(status_code=status.HTTP_204_NO_CONTENT)
