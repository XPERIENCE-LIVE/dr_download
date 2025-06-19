import threading
import time
from queue import Queue

_queue: Queue[str] = Queue()
_progress: dict[str, int] = {}
_history: list[dict[str, str | int]] = []
_state_lock = threading.Lock()
_worker_started = False


def enqueue_download(video_url: str) -> None:
    """Add a video URL to the download queue."""
    global _worker_started
    _queue.put(video_url)
    with _state_lock:
        _progress[video_url] = 0
        _history.append({"url": video_url, "status": "queued"})
    if not _worker_started:
        threading.Thread(target=_worker, daemon=True).start()
        _worker_started = True


def _worker() -> None:
    while True:
        url = _queue.get()
        for i in range(1, 11):
            time.sleep(0.2)
            with _state_lock:
                _progress[url] = i * 10
        with _state_lock:
            _history.append({"url": url, "status": "done"})
        _queue.task_done()


def get_progress(video_url: str) -> int:
    """Return the download progress percentage for the given URL."""
    return _progress.get(video_url, 0)


def get_history() -> list[dict[str, str | int]]:
    """Return the list of past download actions."""
    return list(_history)
