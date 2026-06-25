from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app import models  # noqa: F401
from app.api.routes import router
from app.core.config import PROJECT_ROOT, settings
from app.db import Base, engine, ensure_runtime_schema


@asynccontextmanager
async def lifespan(_: FastAPI):
    for directory in (
        settings.uploads_dir,
        settings.object_storage_root,
        settings.identity_gallery_dir,
    ):
        Path(directory).mkdir(parents=True, exist_ok=True)

    Base.metadata.create_all(bind=engine)
    ensure_runtime_schema(engine)
    yield


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    lifespan=lifespan,
)


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    titles = {
        400: "Bad request",
        401: "Authentication required",
        403: "Forbidden",
        404: "Resource not found",
        409: "Conflict",
        413: "Payload too large",
        422: "Unprocessable entity",
        503: "Service unavailable",
    }
    detail = exc.detail if isinstance(exc.detail, str) else str(exc.detail)
    return JSONResponse(
        status_code=exc.status_code,
        media_type="application/problem+json",
        content={
            "type": "about:blank",
            "title": titles.get(exc.status_code, "Request failed"),
            "status": exc.status_code,
            "detail": detail,
            "instance": str(request.url),
            "errors": [],
        },
        headers=exc.headers,
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    errors = []
    for error in exc.errors():
        location = [str(part) for part in error.get("loc", ()) if part != "body"]
        errors.append(
            {
                "field": ".".join(location) or "body",
                "code": str(error.get("type", "VALIDATION_ERROR")).upper(),
                "message": error.get("msg", "Invalid value"),
            }
        )

    return JSONResponse(
        status_code=422,
        media_type="application/problem+json",
        content={
            "type": "about:blank",
            "title": "Invalid request body",
            "status": 422,
            "detail": "Request validation failed",
            "instance": str(request.url),
            "errors": errors,
        },
    )


app.mount(
    "/static",
    StaticFiles(directory=PROJECT_ROOT / "app" / "web"),
    name="static",
)
app.mount(
    "/media",
    StaticFiles(directory=settings.uploads_dir, check_dir=False),
    name="media",
)
app.mount(
    "/demo-assets",
    StaticFiles(directory=PROJECT_ROOT / "demo_assets"),
    name="demo-assets",
)
app.include_router(router)
