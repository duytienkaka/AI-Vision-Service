from datetime import datetime
from typing import Annotated, Literal, Union

from pydantic import BaseModel, ConfigDict, Field, HttpUrl


class HealthStatus(BaseModel):
    status: Literal["ok"]
    service: str
    time: datetime


class BoundingBox(BaseModel):
    x: float = Field(ge=0, le=1)
    y: float = Field(ge=0, le=1)
    width: float = Field(ge=0, le=1)
    height: float = Field(ge=0, le=1)


class DetectedObject(BaseModel):
    objectType: Literal[
        "PERSON",
        "WHEELCHAIR",
        "STRETCHER",
        "SMOKE",
        "FIRE_EXTINGUISHER",
        "UNKNOWN",
    ]
    confidence: float = Field(ge=0, le=1)
    boundingBox: BoundingBox
    label: str | None = None
    trackId: str | None = None


class ImageUrlSource(BaseModel):
    sourceType: Literal["IMAGE_URL"]
    url: HttpUrl


class ObjectStorageSource(BaseModel):
    sourceType: Literal["OBJECT_STORAGE_REF"]
    bucket: str = Field(min_length=3, max_length=100)
    objectKey: str = Field(min_length=3, max_length=300)
    expiresAt: datetime


ImageSource = Annotated[Union[ImageUrlSource, ObjectStorageSource], Field(discriminator="sourceType")]


class UploadedImageSource(BaseModel):
    sourceType: Literal["UPLOADED_FILE"]
    filename: str
    contentType: str | None = None
    localPath: str


class DetectionRequest(BaseModel):
    requestId: str = Field(pattern=r"^REQ-[A-Z0-9-]+$")
    cameraId: str = Field(pattern=r"^CAM-[A-Z0-9-]+$")
    capturedAt: datetime
    traceId: str = Field(pattern=r"^TRACE-[A-Z0-9-]+$")
    imageSource: ImageSource
    zoneId: str | None = Field(default=None, min_length=2, max_length=80)
    motionLevel: float | None = Field(default=None, ge=0, le=1)
    notes: str | None = Field(default=None, min_length=1, max_length=300)


class DetectionSnapshot(BaseModel):
    status: Literal["PROCESSING", "COMPLETED", "FAILED"]
    confidence: float | None = Field(default=None, ge=0, le=1)
    riskLevel: Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"] | None = None
    modelVersion: str | None = Field(default=None, min_length=3, max_length=100)
    summary: str | None = Field(default=None, min_length=3, max_length=300)
    alertHint: Literal["REVIEW_SECURITY", "MONITOR", "NONE"] | None = None
    completedAt: datetime | None = None
    thumbnailUrl: str | None = None
    objects: list[DetectedObject] = Field(default_factory=list, max_length=50)


class DetectionSubmission(BaseModel):
    detectionId: str = Field(pattern=r"^DET-[0-9]{8}-[0-9]{4}$")
    requestId: str = Field(pattern=r"^REQ-[A-Z0-9-]+$")
    traceId: str = Field(pattern=r"^TRACE-[A-Z0-9-]+$")
    status: Literal["PROCESSING", "COMPLETED", "FAILED"]
    acceptedAt: datetime
    preliminaryResult: DetectionSnapshot | None = None


class DetectionResult(DetectionSnapshot):
    detectionId: str = Field(pattern=r"^DET-[0-9]{8}-[0-9]{4}$")
    requestId: str = Field(pattern=r"^REQ-[A-Z0-9-]+$")
    traceId: str = Field(pattern=r"^TRACE-[A-Z0-9-]+$")
    processedAt: datetime | None = None
    errorDetail: str | None = Field(default=None, max_length=500)


class ModelInfo(BaseModel):
    modelName: str = Field(min_length=3, max_length=100)
    modelVersion: str = Field(min_length=3, max_length=100)
    supportedObjectTypes: list[str] = Field(min_length=1, max_length=20)
    supportedImageSourceTypes: list[str] = Field(min_length=1, max_length=5)
    maxImageSizeBytes: int = Field(ge=1024, le=104857600)
    notes: str | None = Field(default=None, min_length=3, max_length=300)
    lastUpdatedAt: datetime | None = None


class RecognizedPerson(BaseModel):
    trackId: str | None = None
    displayName: str = Field(min_length=1, max_length=120)
    matchConfidence: float = Field(ge=0, le=1)
    detectionConfidence: float = Field(ge=0, le=1)
    boundingBox: BoundingBox
    objectLabel: str | None = Field(default=None, min_length=1, max_length=80)


class IdentityCheckResponse(BaseModel):
    requestId: str = Field(pattern=r"^REQ-[A-Z0-9-]+$")
    traceId: str = Field(pattern=r"^TRACE-[A-Z0-9-]+$")
    status: Literal["COMPLETED", "FAILED"]
    modelVersion: str = Field(min_length=3, max_length=100)
    summary: str = Field(min_length=3, max_length=300)
    processedAt: datetime
    personCount: int = Field(ge=0, le=50)
    recognizedPersons: list[RecognizedPerson] = Field(default_factory=list, max_length=50)
    errorDetail: str | None = Field(default=None, max_length=500)


class IdentityRecord(BaseModel):
    personCode: str = Field(pattern=r"^ID-[A-Z0-9-]+$")
    displayName: str = Field(min_length=1, max_length=120)
    notes: str | None = Field(default=None, min_length=1, max_length=300)
    referenceImageUrl: str
    referenceImageUrls: list[str] = Field(default_factory=list, max_length=50)
    sampleCount: int = Field(ge=0, le=50)
    createdAt: datetime
    updatedAt: datetime


class IdentityRegisterResponse(BaseModel):
    status: Literal["CREATED", "UPDATED"]
    identity: IdentityRecord


class IdentityDeleteResponse(BaseModel):
    status: Literal["DELETED"]
    personCode: str = Field(pattern=r"^ID-[A-Z0-9-]+$")
    deletedSampleCount: int = Field(ge=0, le=1000)


class DemoDetectionResponse(BaseModel):
    detectionId: str = Field(pattern=r"^DET-[0-9]{8}-[0-9]{4}$")
    requestId: str = Field(pattern=r"^REQ-[A-Z0-9-]+$")
    traceId: str = Field(pattern=r"^TRACE-[A-Z0-9-]+$")
    imageUrl: str
    result: DetectionResult


class Problem(BaseModel):
    type: str = "about:blank"
    title: str
    status: int
    detail: str | None = None
    instance: str | None = None
    errors: list[dict] = Field(default_factory=list)

    model_config = ConfigDict(extra="forbid")
