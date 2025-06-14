import yt_dlp
import threading
import uuid
import os
from queue import Queue

download_queue = Queue()
progress_dict = {}
history = []

def enqueue_download(url, format, output_dir, cookies=None):
    task_id = str(uuid.uuid4())
    progress_dict[task_id] = {"status": "queued", "progress": 0}
    download_queue.put((task_id, url, format, output_dir, cookies))
    t = threading.Thread(target=download_worker, daemon=True)
    t.start()
    return task_id

def download_worker():
    while not download_queue.empty():
        task_id, url, format, output_dir, cookies = download_queue.get()
        try:
            ydl_opts = {
                "format": "bestvideo+bestaudio/best" if format == "video" else "bestaudio/best",
                "outtmpl": os.path.join(output_dir, "%(title)s.%(ext)s"),
                "progress_hooks": [lambda d: progress_hook(task_id, d)],
                "noplaylist": False,
            }
            if cookies:
                cookies_path = f"/tmp/{task_id}_cookies.txt"
                with open(cookies_path, "wb") as f:
                    f.write(cookies.file.read())
                ydl_opts["cookiefile"] = cookies_path

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])

            progress_dict[task_id].update({"status": "finished", "progress": 100})
            history.append({"task_id": task_id, "url": url, "status": "ok", "format": format, "output": output_dir})
        except Exception as e:
            progress_dict[task_id].update({"status": "error", "progress": 0, "error": str(e)})
            history.append({"task_id": task_id, "url": url, "status": "error", "format": format, "output": output_dir, "error": str(e)})
        finally:
            download_queue.task_done()

def progress_hook(task_id, d):
    if d["status"] == "downloading":
        total = d.get("total_bytes") or d.get("total_bytes_estimate")
        downloaded = d.get("downloaded_bytes", 0)
        if total:
            percent = min((downloaded / total) * 100, 100)
            progress_dict[task_id].update({"status": "downloading", "progress": percent})

def get_progress(task_id):
    return progress_dict.get(task_id, {"status": "unknown", "progress": 0})

def get_history():
    return history[-10:]
