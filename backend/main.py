from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, ConfigDict
from fastapi.middleware.cors import CORSMiddleware
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


class DownloadRequest(BaseModel):
    url: str
    format: str
    output_dir: str


class ConfigUpdate(BaseModel):
    theme: str
    default_format: str

    model_config = ConfigDict(extra="allow")


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
    save_config(config.model_dump())
    return {"status": "ok"}


@app.post("/shutdown/")
async def shutdown():
    """Stop worker threads and shut down the server."""
    shutdown_workers()
    return {"status": "stopping"}


app.add_event_handler("shutdown", shutdown_workers)


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
