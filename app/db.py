from collections.abc import Generator

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, declarative_base, sessionmaker

from app.core.config import settings

engine = create_engine(settings.database_url, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
Base = declarative_base()


def ensure_runtime_schema(bind: Engine | None = None) -> None:
    bind = bind or engine
    inspector = inspect(bind)
    if "detections" not in inspector.get_table_names():
        return

    existing_columns = {column["name"] for column in inspector.get_columns("detections")}
    required_columns = {
        "person_detected": "BOOLEAN NOT NULL DEFAULT FALSE",
        "known_person_detected": "BOOLEAN NULL",
        "identity_matches_payload": "JSON NOT NULL DEFAULT '[]'",
    }

    with bind.begin() as connection:
        for column_name, column_definition in required_columns.items():
            if column_name in existing_columns:
                continue
            connection.execute(text(f"ALTER TABLE detections ADD COLUMN {column_name} {column_definition}"))


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
