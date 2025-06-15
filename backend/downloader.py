import threading
import time

_download_queue = []
_progress = {}
_history = []
_lock = threading.Lock()


def _worker():
    while True:
        if _download_queue:
            with _lock:
                url = _download_queue.pop(0)
            for i in range(5):
                with _lock:
                    _progress[url] = (i + 1) * 20
                time.sleep(0.5)
            with _lock:
                _history.append(url)
        else:
            time.sleep(0.5)

t = threading.Thread(target=_worker, daemon=True)
t.start()


def enqueue_download(video_url: str) -> None:
    with _lock:
        if video_url not in _progress:
            _progress[video_url] = 0
            _download_queue.append(video_url)


def get_progress(video_url: str) -> int:
    with _lock:
        return _progress.get(video_url, 0)


def get_history() -> list[str]:
    with _lock:
        return list(_history)
