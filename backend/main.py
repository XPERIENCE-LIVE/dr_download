from fastapi import FastAPI, UploadFile, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from downloader import enqueue_download, get_progress, get_history
from config import load_config, save_config
import uvicorn

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/download/")
async def download_media(background_tasks: BackgroundTasks, url: str, format: str, output_dir: str, cookies: UploadFile = None):
    task_id = enqueue_download(url, format, output_dir, cookies)
    background_tasks.add_task(get_progress, task_id)
    return {"task_id": task_id}

@app.get("/progress/{task_id}")
async def check_progress(task_id: str):
    return get_progress(task_id)

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
