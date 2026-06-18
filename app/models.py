from datetime import datetime

from sqlalchemy import JSON, DateTime, Float, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class Detection(Base):
    __tablename__ = "detections"
    __table_args__ = (UniqueConstraint("request_id", name="uq_detections_request_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    detection_id: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    request_id: Mapped[str] = mapped_column(String(64), nullable=False)
    trace_id: Mapped[str] = mapped_column(String(64), nullable=False)
    camera_id: Mapped[str] = mapped_column(String(64), nullable=False)
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    zone_id: Mapped[str | None] = mapped_column(String(80))
    motion_level: Mapped[float | None] = mapped_column(Float)
    notes: Mapped[str | None] = mapped_column(String(300))
    image_source: Mapped[dict] = mapped_column(JSON, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    accepted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    confidence: Mapped[float | None] = mapped_column(Float)
    risk_level: Mapped[str | None] = mapped_column(String(32))
    model_version: Mapped[str | None] = mapped_column(String(100))
    summary: Mapped[str | None] = mapped_column(String(300))
    alert_hint: Mapped[str | None] = mapped_column(String(32))
    thumbnail_url: Mapped[str | None] = mapped_column(Text)
    objects_payload: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    error_detail: Mapped[str | None] = mapped_column(String(500))


class KnownIdentity(Base):
    __tablename__ = "known_identities"
    __table_args__ = (UniqueConstraint("person_code", name="uq_known_identities_person_code"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    person_code: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    display_name: Mapped[str] = mapped_column(String(120), nullable=False)
    notes: Mapped[str | None] = mapped_column(String(300))
    reference_image_path: Mapped[str] = mapped_column(Text, nullable=False)
    embedding_vector: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class IdentityReferenceSample(Base):
    __tablename__ = "identity_reference_samples"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    person_code: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    image_path: Mapped[str] = mapped_column(Text, nullable=False)
    embedding_vector: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
