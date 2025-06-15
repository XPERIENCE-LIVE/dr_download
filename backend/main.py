from fastapi import FastAPI
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from downloader import enqueue_download, get_progress, get_history
from config import load_config, save_config
from utils import setup_logging
import uvicorn

setup_logging()
app = FastAPI()


class DownloadRequest(BaseModel):
    url: str

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/download/")
async def download_media(request: DownloadRequest):
    enqueue_download(request.url)
    return {"status": "queued"}

@app.get("/progress/{video_url}")
async def check_progress(video_url: str):
    return {"progress": get_progress(video_url)}

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
