"""Download queue and worker threads for media retrieval."""

import json
import logging
import os
import threading
import uuid
from queue import Empty, Queue

import yt_dlp

# Maximum number of queued downloads at once
_MAX_QUEUE_SIZE = 100

# Queue of download tasks. Each item is a tuple of
# (task_id, url, format, output_dir)
_queue: Queue[tuple[str, str, str, str]] = Queue(maxsize=_MAX_QUEUE_SIZE)
_progress: dict[str, int] = {}
_history: dict[str, dict[str, str | int]] = {}
# Maximum number of history entries to keep on disk
_MAX_HISTORY_LEN = 1000
_state_lock = threading.Lock()
_worker_started = False
_NUM_WORKERS = 4
stop_event = threading.Event()
_SENTINEL = object()
_workers: list[threading.Thread] = []
HISTORY_FILE = os.path.join(os.path.dirname(__file__), "history.json")


def _load_history() -> None:
    global _history
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r") as f:
                _history = json.load(f)
        except Exception as exc:
            logging.warning(
                "Failed to load history file %s: %s; starting fresh",
                HISTORY_FILE,
                exc,
            )
            _history = {}


def _save_history() -> None:
    # Drop oldest entries exceeding the history limit
    while len(_history) > _MAX_HISTORY_LEN:
        _history.pop(next(iter(_history)))
    try:
        with open(HISTORY_FILE, "w") as f:
            json.dump(_history, f, indent=2)
    except (IOError, OSError) as exc:
        logging.error("Failed to write history file %s: %s", HISTORY_FILE, exc)


_load_history()


def enqueue_download(video_url: str, fmt: str, output_dir: str) -> str:
    """Add a new download request to the queue and return its task ID."""
    global _worker_started
    if stop_event.is_set():
        raise RuntimeError("Workers are shutting down")
    if _queue.full():
        raise RuntimeError("Download queue is full")
    task_id = str(uuid.uuid4())
    _queue.put((task_id, video_url, fmt, output_dir))
    with _state_lock:
        _progress[task_id] = 0
        _history[task_id] = {
            "id": task_id,
            "url": video_url,
            "format": fmt,
            "output_dir": output_dir,
            "status": "queued",
        }
        _save_history()
        if not _worker_started and not stop_event.is_set():
            for _ in range(_NUM_WORKERS):
                if stop_event.is_set():
                    break
                t = threading.Thread(target=_worker, daemon=True)
                _workers.append(t)
                t.start()
            _worker_started = True
    return task_id


def _worker() -> None:
    """Process queued downloads until signalled to stop."""
    while True:
        if stop_event.is_set():
            break
        task_id = url = fmt = out_dir = None
        status = "error"
        got_item = False
        try:
            item = _queue.get(timeout=0.1)
            if item is _SENTINEL:
                _queue.task_done()
                break
            task_id, url, fmt, out_dir = item
            got_item = True
            try:
                os.makedirs(out_dir, exist_ok=True)
            except OSError as exc:
                logging.error(
                    "Cannot create output directory %s: %s",
                    out_dir,
                    exc,
                )
                status = "error"
                _queue.task_done()
                got_item = False
                continue
            output_template = os.path.join(out_dir, "%(title)s.%(ext)s")

            def progress_hook(d: dict) -> None:
                if d.get("status") == "downloading":
                    total = d.get("total_bytes") or d.get(
                        "total_bytes_estimate"
                    )  # noqa: E501
                    downloaded = d.get("downloaded_bytes", 0)
                    if total:
                        percent = int(downloaded / total * 100)
                        with _state_lock:
                            _progress[task_id] = percent

            ydl_opts = {
                "outtmpl": output_template,
                "progress_hooks": [progress_hook],
            }

            if fmt == "audio":
                ydl_opts.update(
                    {
                        "format": "bestaudio/best",
                        "postprocessors": [
                            {
                                "key": "FFmpegExtractAudio",
                                "preferredcodec": "mp3",
                            }
                        ],
                    }
                )

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
            status = "done"
        except Empty:
            continue
        except yt_dlp.utils.DownloadError as exc:
            logging.error("Download failed for %s: %s", url, exc)
            status = "error"
        except Exception:
            logging.exception(
                "Unexpected error while processing task %s", task_id
            )  # noqa: E501
            status = "error"
        finally:
            if task_id is not None:
                with _state_lock:
                    entry = _history.get(
                        task_id,
                        {
                            "id": task_id,
                            "url": url,
                            "format": fmt,
                            "output_dir": out_dir,
                        },
                    )
                    entry["status"] = status
                    _history[task_id] = entry
                    _save_history()
                    _progress.pop(task_id, None)
            if got_item:
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


def shutdown_workers() -> None:
    """Signal the worker threads to stop and wait for them to finish."""
    if not _workers:
        return
    stop_event.set()
    for _ in _workers:
        _queue.put(_SENTINEL)
    for t in list(_workers):
        t.join(timeout=5)
        if t.is_alive():
            logging.warning("Worker thread %s did not exit in time", t.name)
    _workers.clear()
    global _worker_started
    _worker_started = False
    stop_event.clear()
