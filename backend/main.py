from fastapi import FastAPI, HTTPException, Request
import logging
import shutil
from pydantic import BaseModel, Field, HttpUrl, ValidationError, conint
try:
    from pydantic import TypeAdapter
except ImportError:  # pragma: no cover - pydantic<2
    TypeAdapter = None
    from pydantic import parse_obj_as
try:
    from pydantic import ConfigDict
except ImportError:  # pragma: no cover - pydantic<2
    ConfigDict = None
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.exception_handlers import request_validation_exception_handler
from fastapi.responses import JSONResponse
from .downloader import (
    cancel_download,
    delete_download,
    enqueue_download,
    enqueue_premium_download,
    get_download,
    get_progress,
    get_history,
    list_downloads,
    retry_download,
    start_download_workers,
    shutdown_workers,
)
from .media_service import COOKIE_SOURCES, inspect_media
from .engine_updater import ensure_engine_ready
from .error_mapping import classify_error
from .config import authorized_cookie_source, load_config, save_config
from .utils import setup_logging
from .directory_service import ensure_output_directory
from .engine_runner import FORMAT_ID_PATTERN
import uvicorn
import os

setup_logging()
app = FastAPI()
SESSION_TOKEN = os.getenv("DR_DOWNLOAD_TOKEN", "")


@app.middleware("http")
async def require_session_token(request: Request, call_next):
    """Reject callers outside the Electron-owned local session."""
    if SESSION_TOKEN and request.headers.get("X-Dr-Download-Token") != SESSION_TOKEN:
        return JSONResponse(
            status_code=401,
            content={"detail": {"code": "unauthorized", "message": "Invalid session"}},
        )
    return await call_next(request)


@app.exception_handler(RequestValidationError)
async def download_validation_exception_handler(request: Request, exc: RequestValidationError):
    """Return 400 for malformed download URLs."""
    if request.url.path == "/download/":
        for err in exc.errors():
            if "url" in err.get("loc", []):
                return JSONResponse(status_code=400, content={"detail": "Malformed URL"})
    return await request_validation_exception_handler(request, exc)


class DownloadRequest(BaseModel):
    url: str
    format: str
    output_dir: str

    if hasattr(BaseModel, "model_validate"):
        # pydantic v2
        from pydantic import field_validator

        @field_validator("url")
        @classmethod
        def validate_url(cls, v: str) -> str:
            try:
                if TypeAdapter:
                    TypeAdapter(HttpUrl).validate_python(v)
                else:  # pragma: no cover - pydantic<2
                    parse_obj_as(HttpUrl, v)
            except ValidationError:
                raise ValueError("Invalid URL")
            return v
    else:  # pragma: no cover - pydantic<2
        from pydantic import validator, parse_obj_as

        @validator("url")
        def validate_url(cls, v: str) -> str:
            try:
                parse_obj_as(HttpUrl, v)
            except ValidationError:
                raise ValueError("Invalid URL")
            return v


class ConfigUpdate(BaseModel):
    theme: str
    default_format: str

    if hasattr(BaseModel, "model_dump"):  # pydantic v2
        model_config = ConfigDict(extra="allow")
    else:  # pragma: no cover - pydantic<2
        class Config:
            extra = "allow"


class InspectRequest(BaseModel):
    url: HttpUrl
    cookie_source: str = "none"


class PremiumDownloadRequest(BaseModel):
    url: HttpUrl
    format_id: str = Field(**{
        "pattern" if hasattr(BaseModel, "model_validate") else "regex": FORMAT_ID_PATTERN
    })
    output_dir: str
    cookie_source: str = "none"
    estimated_bytes: conint(strict=True, ge=0, le=9007199254740991) | None = None


class DirectoryValidationRequest(BaseModel):
    path: str


origins_env = os.getenv("ALLOW_ORIGINS")
if origins_env:
    allowed_origins = [
        origin.strip() for origin in origins_env.split(",") if origin.strip()
    ]
else:
    allowed_origins = ["http://localhost:3000", "http://localhost:5173"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _not_found():
    raise HTTPException(
        status_code=404,
        detail={
            "code": "download_not_found",
            "message": "No se encontró la descarga.",
            "recovery": "Actualiza la cola o el historial.",
        },
    )


@app.post("/media/inspect")
async def inspect_media_endpoint(request: InspectRequest):
    if request.cookie_source not in COOKIE_SOURCES:
        raise HTTPException(status_code=400, detail="Unsupported cookie source")
    if request.cookie_source != authorized_cookie_source(request.cookie_source):
        raise HTTPException(status_code=403, detail=classify_error("Browser consent required"))
    try:
        return inspect_media(str(request.url), request.cookie_source)
    except Exception as exc:
        logging.warning("Media inspection failed: %s", type(exc).__name__)
        raise HTTPException(
            status_code=400,
            detail=classify_error(str(exc), request.cookie_source),
        )


@app.post("/downloads")
async def create_download(request: PremiumDownloadRequest):
    if request.cookie_source not in COOKIE_SOURCES:
        raise HTTPException(status_code=400, detail="Unsupported cookie source")
    if request.cookie_source != authorized_cookie_source(request.cookie_source):
        raise HTTPException(status_code=403, detail=classify_error("Browser consent required"))
    directory = ensure_output_directory(request.output_dir, min_free_bytes=0)
    if not directory.valid:
        raise HTTPException(status_code=400, detail=directory.as_dict())
    # Advisory staging/conversion headroom; worker disk errors remain authoritative.
    required_bytes = max(128 * 1024 * 1024, 2 * (request.estimated_bytes or 0))
    if shutil.disk_usage(directory.path).free < required_bytes:
        raise HTTPException(
            status_code=400,
            detail=classify_error("No space left on device", request.cookie_source),
        )
    try:
        return enqueue_premium_download(
            str(request.url), request.format_id, directory.path, request.cookie_source
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.post("/directories/validate")
async def validate_directory(request: DirectoryValidationRequest):
    """Create/check a destination folder before the user queues a download."""
    return ensure_output_directory(request.path).as_dict()


@app.get("/downloads")
async def downloads_collection():
    return list_downloads()


@app.get("/downloads/{task_id}")
async def download_detail(task_id: str):
    return get_download(task_id) or _not_found()


@app.post("/downloads/{task_id}/cancel")
async def cancel_download_endpoint(task_id: str):
    if not cancel_download(task_id):
        return _not_found()
    return get_download(task_id)


@app.post("/downloads/{task_id}/retry")
async def retry_download_endpoint(task_id: str):
    return retry_download(task_id) or _not_found()


@app.delete("/downloads/{task_id}")
async def delete_download_endpoint(task_id: str):
    if not delete_download(task_id):
        return _not_found()
    return {"status": "deleted"}


@app.get("/health")
async def health():
    return {"status": "ok", "product": "Dr. Download"}


@app.post("/download/")
async def download_media(request: DownloadRequest):
    """Queue a new download task."""
    if request.format not in ("audio", "video"):
        raise HTTPException(
            status_code=400,
            detail="Format must be 'audio' or 'video'",
        )
    if not request.output_dir or not os.path.isdir(request.output_dir):
        raise HTTPException(
            status_code=400,
            detail="Output directory required",
        )
    if not os.access(request.output_dir, os.W_OK):
        raise HTTPException(
            status_code=400,
            detail="Output directory not writable",
        )
    task_id = enqueue_download(request.url, request.format, request.output_dir)
    return {"status": "queued", "task_id": task_id}


@app.get("/progress/{task_id}")
async def check_progress(task_id: str):
    """Return progress and current status for a task."""
    status = get_history().get(task_id, {}).get("status", "unknown")
    return {"progress": get_progress(task_id), "status": status}


@app.get("/history/")
async def get_download_history():
    """Return details about past downloads."""
    return get_history()


@app.get("/config/")
async def get_config():
    """Return the current configuration."""
    return load_config()


@app.post("/config/")
@app.put("/config")
async def update_config(config: ConfigUpdate):
    """Update the configuration on disk."""
    if hasattr(config, "model_dump"):
        data = config.model_dump()
    else:
        data = config.dict()
    try:
        save_config(data)
    except Exception:
        logging.exception("Failed to save configuration")
        raise HTTPException(status_code=500, detail="Failed to save configuration")
    return {"status": "ok"}


@app.post("/shutdown/")
async def shutdown():
    """Stop worker threads and shut down the server."""
    shutdown_workers()
    return {"status": "stopping"}


app.add_event_handler("shutdown", shutdown_workers)


def start_engine_updater():
    config = load_config()
    data_dir = os.getenv("DR_DOWNLOAD_DATA_DIR") or os.path.join(
        os.getenv("LOCALAPPDATA", os.path.dirname(__file__)), "DrDownload"
    )
    return ensure_engine_ready(data_dir, bool(config.get("auto_update_engine", True)))


app.add_event_handler("startup", start_engine_updater)
app.add_event_handler("startup", start_download_workers)


if __name__ == "__main__":
    uvicorn.run(
        app,
        host="127.0.0.1",
        port=int(os.getenv("DR_DOWNLOAD_PORT", "8000")),
    )
