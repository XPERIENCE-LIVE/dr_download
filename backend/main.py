from fastapi import FastAPI
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from downloader import enqueue_download, get_progress, get_history
from config import load_config, save_config
from utils import setup_logging
import uvicorn
import os

setup_logging()
app = FastAPI()


class DownloadRequest(BaseModel):
    url: str

origins_env = os.getenv("ALLOW_ORIGINS")
if origins_env:
    allowed_origins = [origin.strip() for origin in origins_env.split(',') if origin.strip()]
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
    task_id = enqueue_download(request.url)
    return {"status": "queued", "task_id": task_id}

@app.get("/progress/{task_id}")
async def check_progress(task_id: str):
    return {"progress": get_progress(task_id)}

@app.get("/history/")
async def get_download_history():
    return get_history()

@app.get("/config/")
async def get_config():
    return load_config()

@app.post("/config/")
async def update_config(config: dict):
    save_config(config)
    return {"status": "ok"}

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
