from fastapi import FastAPI, HTTPException, Request
import logging
from pydantic import BaseModel, HttpUrl, ValidationError
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
    enqueue_download,
    get_progress,
    get_history,
    shutdown_workers,
)
from .config import load_config, save_config
from .utils import setup_logging
import uvicorn
import os

setup_logging()
app = FastAPI()


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
    """Return progress percentage for a task."""
    return {"progress": get_progress(task_id)}


@app.get("/history/")
async def get_download_history():
    """Return details about past downloads."""
    return get_history()


@app.get("/config/")
async def get_config():
    """Return the current configuration."""
    return load_config()


@app.post("/config/")
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


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
