from collections.abc import Generator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

import app.main as main_module
from app.db import Base, get_db
from app.main import app


@pytest.fixture()
def client(tmp_path: Path) -> Generator[TestClient, None, None]:
    db_path = tmp_path / "test.db"
    engine = create_engine(f"sqlite:///{db_path}", future=True)
    TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
    Base.metadata.create_all(bind=engine)
    uploads_dir = tmp_path / "uploads"
    object_store_dir = tmp_path / "object_store"
    identity_gallery_dir = tmp_path / "identity_gallery"
    uploads_dir.mkdir(parents=True, exist_ok=True)
    object_store_dir.mkdir(parents=True, exist_ok=True)
    identity_gallery_dir.mkdir(parents=True, exist_ok=True)

    def override_get_db() -> Generator[Session, None, None]:
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    original_engine = main_module.engine
    original_uploads_dir = main_module.settings.uploads_dir
    original_object_storage_root = main_module.settings.object_storage_root
    original_identity_gallery_dir = main_module.settings.identity_gallery_dir
    main_module.engine = engine
    main_module.settings.uploads_dir = str(uploads_dir)
    main_module.settings.object_storage_root = str(object_store_dir)
    main_module.settings.identity_gallery_dir = str(identity_gallery_dir)

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()
    main_module.engine = original_engine
    main_module.settings.uploads_dir = original_uploads_dir
    main_module.settings.object_storage_root = original_object_storage_root
    main_module.settings.identity_gallery_dir = original_identity_gallery_dir
    Base.metadata.drop_all(bind=engine)
