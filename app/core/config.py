from pathlib import Path

from pydantic import ConfigDict
from pydantic_settings import BaseSettings

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _resolve_project_path(value: str) -> str:
    path = Path(value)
    if path.is_absolute():
        return str(path)
    return str((PROJECT_ROOT / path).resolve())


class Settings(BaseSettings):
    app_name: str = "AI Vision Detection API"
    app_version: str = "1.0.0"
    database_url: str = "postgresql+psycopg://postgres:postgres@db:5432/ai_vision"
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    core_service_url: str | None = None
    core_service_timeout_seconds: float = 5.0
    yolo_model_name: str = "yolov8n.pt"
    image_fetch_timeout_seconds: float = 15.0
    max_image_size_bytes: int = 5242880
    identity_match_threshold: float = 0.92
    yolo_config_dir: str = str(PROJECT_ROOT / ".ultralytics")
    torch_home: str = str(PROJECT_ROOT / ".torch")
    uploads_dir: str = str(PROJECT_ROOT / "storage" / "uploads")
    object_storage_root: str = str(PROJECT_ROOT / "storage" / "object_store")
    identity_gallery_dir: str = str(PROJECT_ROOT / "storage" / "identity_gallery")
    demo_title: str = "AI Vision Demo Console"

    model_config = ConfigDict(env_file=".env", env_file_encoding="utf-8")


settings = Settings()
settings.yolo_config_dir = _resolve_project_path(settings.yolo_config_dir)
settings.torch_home = _resolve_project_path(settings.torch_home)
settings.uploads_dir = _resolve_project_path(settings.uploads_dir)
settings.object_storage_root = _resolve_project_path(settings.object_storage_root)
settings.identity_gallery_dir = _resolve_project_path(settings.identity_gallery_dir)
