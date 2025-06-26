import threading
import time
from queue import Queue
import uuid

_queue: Queue[tuple[str, str]] = Queue()
_progress: dict[str, int] = {}
_history: dict[str, dict[str, str | int]] = {}
_state_lock = threading.Lock()
_worker_started = False


def enqueue_download(video_url: str) -> str:
    """Add a video URL to the download queue and return a task ID."""
    global _worker_started
    task_id = str(uuid.uuid4())
    _queue.put((task_id, video_url))
    with _state_lock:
        _progress[task_id] = 0
        _history[task_id] = {"id": task_id, "url": video_url, "status": "queued"}
    if not _worker_started:
        threading.Thread(target=_worker, daemon=True).start()
        _worker_started = True
    return task_id


def _worker() -> None:
    while True:
        task_id, url = _queue.get()
        for i in range(1, 11):
            time.sleep(0.2)
            with _state_lock:
                _progress[task_id] = i * 10
        with _state_lock:
            if task_id in _history:
                _history[task_id]["status"] = "done"
            else:
                _history[task_id] = {"id": task_id, "url": url, "status": "done"}
            _progress.pop(task_id, None)
        _queue.task_done()


def get_progress(task_id: str) -> int:
    """Return the download progress percentage for the given task."""
    with _state_lock:
        if task_id in _progress:
            return _progress[task_id]
        if task_id in _history and _history[task_id].get("status") == "done":
            return 100
        return 0


def get_history() -> dict[str, dict[str, str | int]]:
    """Return the dictionary of past download actions keyed by task ID."""
    with _state_lock:
        return dict(_history)
