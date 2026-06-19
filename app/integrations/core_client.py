import httpx

from app import schemas
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


def build_core_detection_notification(
    *,
    result: schemas.DetectionResult,
    camera_id: str,
    captured_at,
    zone_id: str | None,
) -> schemas.CoreDetectionNotification:
    event_type = "VISION_DETECTION_COMPLETED" if result.status == "COMPLETED" else "VISION_DETECTION_FAILED"
    return schemas.CoreDetectionNotification(
        eventId=f"EVT-VISION-{result.detectionId.removeprefix('DET-')}",
        eventType=event_type,
        sentAt=result.processedAt or result.completedAt or captured_at,
        detectionId=result.detectionId,
        requestId=result.requestId,
        traceId=result.traceId,
        cameraId=camera_id,
        zoneId=zone_id,
        capturedAt=captured_at,
        processedAt=result.processedAt or result.completedAt or captured_at,
        personDetected=result.personDetected,
        knownPersonDetected=result.knownPersonDetected,
        confidence=result.confidence,
        riskLevel=result.riskLevel,
        summary=result.summary,
        alertHint=result.alertHint,
        identityMatches=result.identityMatches,
        objects=result.objects,
    )


def send_detection_to_core(notification: schemas.CoreDetectionNotification) -> None:
    if not settings.core_service_url:
        logger.warning("CORE_SERVICE_URL is not configured; skipping Core integration")
        return

    url = f"{settings.core_service_url.rstrip('/')}/api/v1/vision-events"
    payload = notification.model_dump(mode="json")

    try:
        response = httpx.post(
            url,
            json=payload,
            timeout=settings.core_service_timeout_seconds,
        )
        response.raise_for_status()
        logger.info("Sent detection event %s to Core at %s", notification.detectionId, url)
    except httpx.TimeoutException:
        logger.warning(
            "Timed out after %.1fs while sending detection %s to Core",
            settings.core_service_timeout_seconds,
            notification.detectionId,
        )
    except httpx.HTTPStatusError as exc:
        logger.warning(
            "Core returned HTTP %s for detection %s",
            exc.response.status_code,
            notification.detectionId,
        )
    except httpx.RequestError as exc:
        logger.warning(
            "Failed to connect to Core for detection %s: %s",
            notification.detectionId,
            exc,
        )
