import threading
import time
from queue import Queue
import uuid

_queue: Queue[tuple[str, str]] = Queue()
_progress: dict[str, int] = {}
_history: list[dict[str, str | int]] = []
_state_lock = threading.Lock()
_worker_started = False


def enqueue_download(video_url: str) -> str:
    """Add a video URL to the download queue and return a task ID."""
    global _worker_started
    task_id = str(uuid.uuid4())
    _queue.put((task_id, video_url))
    with _state_lock:
        _progress[task_id] = 0
        _history.append({"id": task_id, "url": video_url, "status": "queued"})
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
            _history.append({"id": task_id, "url": url, "status": "done"})
        _queue.task_done()


def get_progress(task_id: str) -> int:
    """Return the download progress percentage for the given task."""
    return _progress.get(task_id, 0)


def get_history() -> list[dict[str, str | int]]:
    """Return the list of past download actions."""
    return list(_history)
