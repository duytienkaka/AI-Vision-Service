import random
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app import models, schemas


def _generate_detection_id() -> str:
    now = datetime.now(timezone.utc)
    return f"DET-{now:%Y%m%d}-{random.randint(0, 9999):04d}"


def get_detection_by_request_id(db: Session, request_id: str) -> models.Detection | None:
    return (
        db.query(models.Detection)
        .filter(models.Detection.request_id == request_id)
        .one_or_none()
    )


def get_detection_by_detection_id(db: Session, detection_id: str) -> models.Detection | None:
    return (
        db.query(models.Detection)
        .filter(models.Detection.detection_id == detection_id)
        .one_or_none()
    )


def create_detection_record(
    db: Session,
    *,
    request_id: str,
    trace_id: str,
    camera_id: str,
    captured_at: datetime,
    zone_id: str | None,
    motion_level: float | None,
    notes: str | None,
    image_source: dict,
) -> models.Detection:
    accepted_at = datetime.now(timezone.utc)
    detection = models.Detection(
        detection_id=_generate_detection_id(),
        request_id=request_id,
        trace_id=trace_id,
        camera_id=camera_id,
        captured_at=captured_at,
        zone_id=zone_id,
        motion_level=motion_level,
        notes=notes,
        image_source=image_source,
        status="PROCESSING",
        accepted_at=accepted_at,
        model_version=None,
        objects_payload=[],
    )
    db.add(detection)
    db.commit()
    db.refresh(detection)
    return detection


def create_detection(db: Session, payload: schemas.DetectionRequest) -> models.Detection:
    return create_detection_record(
        db,
        request_id=payload.requestId,
        trace_id=payload.traceId,
        camera_id=payload.cameraId,
        captured_at=payload.capturedAt,
        zone_id=payload.zoneId,
        motion_level=payload.motionLevel,
        notes=payload.notes,
        image_source=payload.imageSource.model_dump(mode="json"),
    )


def update_detection_result(
    db: Session,
    detection_pk: int,
    result: schemas.DetectionResult,
) -> models.Detection:
    detection = db.query(models.Detection).filter(models.Detection.id == detection_pk).one()
    detection.status = result.status
    detection.processed_at = result.processedAt or datetime.now(timezone.utc)
    detection.completed_at = result.completedAt
    detection.confidence = result.confidence
    detection.risk_level = result.riskLevel
    detection.model_version = result.modelVersion
    detection.summary = result.summary
    detection.alert_hint = result.alertHint
    detection.thumbnail_url = str(result.thumbnailUrl) if result.thumbnailUrl else None
    detection.objects_payload = [item.model_dump(mode="json") for item in result.objects]
    detection.error_detail = result.errorDetail

    db.add(detection)
    db.commit()
    db.refresh(detection)
    return detection


def get_known_identity_by_person_code(db: Session, person_code: str) -> models.KnownIdentity | None:
    return (
        db.query(models.KnownIdentity)
        .filter(models.KnownIdentity.person_code == person_code)
        .one_or_none()
    )


def list_known_identities(db: Session) -> list[models.KnownIdentity]:
    return db.query(models.KnownIdentity).order_by(models.KnownIdentity.display_name.asc()).all()


def list_identity_reference_samples(
    db: Session,
    person_code: str,
) -> list[models.IdentityReferenceSample]:
    return (
        db.query(models.IdentityReferenceSample)
        .filter(models.IdentityReferenceSample.person_code == person_code)
        .order_by(models.IdentityReferenceSample.created_at.asc(), models.IdentityReferenceSample.id.asc())
        .all()
    )


def create_identity_reference_sample(
    db: Session,
    *,
    person_code: str,
    image_path: str,
    embedding_vector: list[float],
) -> models.IdentityReferenceSample:
    sample = models.IdentityReferenceSample(
        person_code=person_code,
        image_path=image_path,
        embedding_vector=embedding_vector,
        created_at=datetime.now(timezone.utc),
    )
    db.add(sample)
    db.commit()
    db.refresh(sample)
    return sample


def upsert_known_identity(
    db: Session,
    *,
    person_code: str,
    display_name: str,
    notes: str | None,
    reference_image_path: str,
    embedding_vector: list[float],
) -> tuple[models.KnownIdentity, str]:
    now = datetime.now(timezone.utc)
    existing = get_known_identity_by_person_code(db, person_code)
    if existing:
        existing.display_name = display_name
        existing.notes = notes
        existing.reference_image_path = reference_image_path
        existing.embedding_vector = embedding_vector
        existing.updated_at = now
        db.add(existing)
        db.commit()
        db.refresh(existing)
        return existing, "UPDATED"

    identity = models.KnownIdentity(
        person_code=person_code,
        display_name=display_name,
        notes=notes,
        reference_image_path=reference_image_path,
        embedding_vector=embedding_vector,
        created_at=now,
        updated_at=now,
    )
    db.add(identity)
    db.commit()
    db.refresh(identity)
    return identity, "CREATED"


def delete_known_identity(db: Session, person_code: str) -> tuple[bool, list[models.IdentityReferenceSample]]:
    identity = get_known_identity_by_person_code(db, person_code)
    if identity is None:
        return False, []

    samples = list_identity_reference_samples(db, person_code)
    for sample in samples:
        db.delete(sample)
    db.delete(identity)
    db.commit()
    return True, samples
