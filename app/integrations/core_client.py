import httpx

from app import schemas
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


def send_detection_to_core(result: schemas.DetectionResult) -> None:
    if not settings.core_service_url:
        logger.warning("CORE_SERVICE_URL is not configured; skipping Core integration")
        return

    url = f"{settings.core_service_url.rstrip('/')}/api/v1/detections"
    payload = result.model_dump(mode="json")

    try:
        response = httpx.post(
            url,
            json=payload,
            timeout=settings.core_service_timeout_seconds,
        )
        response.raise_for_status()
        logger.info("Sent detection %s to Core at %s", result.detectionId, url)
    except httpx.TimeoutException:
        logger.warning(
            "Timed out after %.1fs while sending detection %s to Core",
            settings.core_service_timeout_seconds,
            result.detectionId,
        )
    except httpx.HTTPStatusError as exc:
        logger.warning(
            "Core returned HTTP %s for detection %s",
            exc.response.status_code,
            result.detectionId,
        )
    except httpx.RequestError as exc:
        logger.warning(
            "Failed to connect to Core for detection %s: %s",
            result.detectionId,
            exc,
        )
