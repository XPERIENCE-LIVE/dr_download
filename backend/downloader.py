"""Download queue and worker threads for media retrieval."""

import logging
import os
import threading
import uuid
from queue import Empty, Full, Queue

from .config import DEFAULT_CONFIG, load_config
from .store import DownloadStore
from .engine_runner import download_with_cookie_fallback, resolve_engine
from .error_mapping import classify_error

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
_NUM_WORKERS = DEFAULT_CONFIG["worker_threads"]
stop_event = threading.Event()
_SENTINEL = object()
_workers: list[threading.Thread] = []
_cancel_events: dict[str, threading.Event] = {}
HISTORY_FILE = os.path.join(os.path.dirname(__file__), "history.json")
_DATA_DIR = os.environ.get("DR_DOWNLOAD_DATA_DIR") or os.path.join(
    os.environ.get("LOCALAPPDATA", os.path.dirname(__file__)), "DrDownload"
)
DATABASE_FILE = os.path.join(_DATA_DIR, "downloads.db")
_store = DownloadStore(DATABASE_FILE)


def _recover_loaded_history(records: dict[str, dict]) -> tuple[dict[str, dict], list[tuple]]:
    recovered = {task_id: dict(entry) for task_id, entry in records.items()}
    waiting = []
    for task_id, entry in recovered.items():
        if entry.get("status") == "queued":
            waiting.append(
                (
                    task_id,
                    str(entry.get("url") or ""),
                    str(entry.get("format") or "video"),
                    str(entry.get("output_dir") or ""),
                    str(entry.get("format_id") or "video-best"),
                    str(entry.get("cookie_source") or "none"),
                )
            )
        elif entry.get("status") in {"inspecting", "downloading", "postprocessing"}:
            entry["status"] = "failed"
            entry["error"] = {
                "code": "interrupted",
                "message": "La descarga fue interrumpida al cerrar la aplicación.",
                "recovery": "Reintenta la descarga desde el historial.",
            }
    return recovered, waiting


def _load_history() -> None:
    global _history
    _store.migrate_json(HISTORY_FILE)
    stored = _store.list()
    loaded = {item["id"]: item for item in reversed(stored)}
    _history, waiting = _recover_loaded_history(loaded)
    for entry in _history.values():
        task_id = str(entry["id"])
        _progress[task_id] = int(entry.get("progress") or 0)
        _cancel_events[task_id] = threading.Event()
    for item in waiting:
        try:
            _queue.put_nowait(item)
        except Full as exc:
            raise RuntimeError("persisted queue exceeds runtime capacity") from exc
    if loaded:
        _save_history()


def _save_history() -> None:
    # Drop oldest entries exceeding the history limit
    while len(_history) > _MAX_HISTORY_LEN:
        _history.pop(next(iter(_history)))
    _store.replace_all(list(_history.values()))


_load_history()


def start_download_workers() -> None:
    global _worker_started
    if _worker_started or stop_event.is_set():
        return
    count = max(1, int(load_config().get("worker_threads", _NUM_WORKERS)))
    for _ in range(count):
        worker = threading.Thread(target=_worker, daemon=True)
        _workers.append(worker)
        worker.start()
    _worker_started = True


def enqueue_download(
    video_url: str,
    fmt: str,
    output_dir: str,
    format_id: str | None = None,
    cookie_source: str = "firefox",
    task_id: str | None = None,
) -> str:
    """Add a new download request to the queue and return its task ID."""
    global _worker_started
    if stop_event.is_set():
        raise RuntimeError("Workers are shutting down")
    if _queue.full():
        raise RuntimeError("Download queue is full")
    task_id = task_id or str(uuid.uuid4())
    selected_format = format_id or ("audio-mp3" if fmt == "audio" else "video-best")
    _queue.put((task_id, video_url, fmt, output_dir, selected_format, cookie_source))
    with _state_lock:
        _progress[task_id] = 0
        _history[task_id] = {
            "id": task_id,
            "url": video_url,
            "format": fmt,
            "output_dir": output_dir,
            "status": "queued",
            "progress": 0,
            "format_id": selected_format,
            "cookie_source": cookie_source,
        }
        _cancel_events[task_id] = threading.Event()
        _save_history()
        start_download_workers()
    return task_id


def _record_progress(task_id: str, data: dict) -> None:
    total = data.get("total_bytes") or data.get("total_bytes_estimate")
    downloaded = data.get("bytes_downloaded", data.get("downloaded_bytes", 0))
    percent = data.get("progress")
    if percent is None and total:
        percent = int(downloaded / total * 100)
    if percent is None:
        return
    with _state_lock:
        _progress[task_id] = int(percent)
        _history[task_id].update(
            {
                "status": "downloading",
                "progress": int(percent),
                "bytes_downloaded": downloaded,
                "total_bytes": total,
                "speed_bps": data.get("speed_bps", data.get("speed")),
                "eta_seconds": data.get("eta_seconds", data.get("eta")),
                "filename": data.get("filename"),
            }
        )


def _worker() -> None:
    """Process queued downloads until signalled to stop."""
    while True:
        task_id = url = fmt = out_dir = None
        cookie_source = "none"
        status = "error"
        error_info = None
        got_item = False
        try:
            item = _queue.get(timeout=0.1)
            if item is _SENTINEL:
                _queue.task_done()
                if stop_event.is_set():
                    break
                else:
                    continue
            if stop_event.is_set():
                _queue.task_done()
                continue
            if len(item) != 6:
                raise RuntimeError("Invalid queued download contract")
            task_id, url, fmt, out_dir, format_id, cookie_source = item
            got_item = True
            cancel_event = _cancel_events.setdefault(task_id, threading.Event())
            if cancel_event.is_set():
                status = "cancelled"
                continue
            with _state_lock:
                _history.setdefault(task_id, {})["status"] = "inspecting"
                _save_history()
            try:
                os.makedirs(out_dir, exist_ok=True)
            except OSError as exc:
                logging.error(
                    "Cannot prepare output for task %s (%s)",
                    task_id,
                    type(exc).__name__,
                )
                status = "failed"
                error_info = classify_error(str(exc), cookie_source)
                _queue.task_done()
                got_item = False
                continue
            engine = resolve_engine()
            filename = download_with_cookie_fallback(
                engine,
                url,
                format_id,
                out_dir,
                cookie_source,
                lambda data: _record_progress(task_id, data),
                cancel_event,
            )
            if filename:
                with _state_lock:
                    _history[task_id]["filename"] = filename
            status = "completed"
        except Empty:
            if stop_event.is_set():
                break
            continue
        except RuntimeError as exc:
            if task_id and _cancel_events.get(task_id, threading.Event()).is_set():
                status = "cancelled"
            else:
                logging.error("External engine failed for task %s (%s)", task_id, type(exc).__name__)
                status = "failed"
                error_info = classify_error(str(exc), cookie_source)
        except Exception as exc:
            logging.error(
                "Unexpected error while processing task %s (%s)",
                task_id,
                type(exc).__name__,
            )
            status = "failed"
            error_info = classify_error(str(exc), cookie_source or "none")
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
                    entry["progress"] = 100 if status == "completed" else _progress.get(task_id, 0)
                    if status == "failed":
                        entry["error"] = error_info or classify_error("", cookie_source or "none")
                    elif status in {"completed", "cancelled"}:
                        entry.pop("error", None)
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
        if task_id in _history and _history[task_id].get("status") in ("done", "completed"):
            return 100
        return 0


def get_history() -> dict[str, dict[str, str | int]]:
    """Return the dictionary of past download actions keyed by task ID."""
    with _state_lock:
        return dict(_history)


def enqueue_premium_download(
    video_url: str,
    format_id: str,
    output_dir: str,
    cookie_source: str = "none",
) -> dict:
    kind = "audio" if format_id.startswith("audio") else "video"
    task_id = enqueue_download(video_url, kind, output_dir, format_id, cookie_source)
    return get_download(task_id) or {"id": task_id, "status": "queued", "progress": 0}


def list_downloads() -> list[dict]:
    with _state_lock:
        return list(reversed(list(_history.values())))


def get_download(task_id: str) -> dict | None:
    with _state_lock:
        value = _history.get(task_id)
        return dict(value) if value else None


def cancel_download(task_id: str) -> bool:
    with _state_lock:
        if task_id not in _history or _history[task_id].get("status") in {
            "completed", "failed", "cancelled", "done", "error"
        }:
            return False
        _cancel_events.setdefault(task_id, threading.Event()).set()
        _history[task_id]["status"] = "cancelled"
        _save_history()
        return True


def retry_download(task_id: str) -> dict | None:
    previous = get_download(task_id)
    if not previous or previous.get("status") not in {"failed", "cancelled", "error"}:
        return None
    format_id = str(previous.get("format_id") or "video-best")
    enqueue_download(
        str(previous["url"]),
        "audio" if format_id.startswith("audio") else "video",
        str(previous["output_dir"]),
        format_id,
        str(previous.get("cookie_source") or "none"),
        task_id=task_id,
    )
    return get_download(task_id)


def delete_download(task_id: str) -> bool:
    with _state_lock:
        entry = _history.get(task_id)
        if not entry or entry.get("status") not in {"completed", "failed", "cancelled", "done", "error"}:
            return False
        del _history[task_id]
        try:
            _store.delete(task_id)
        except Exception as exc:
            logging.error("Failed to delete SQLite history: %s", exc)
        _progress.pop(task_id, None)
        _cancel_events.pop(task_id, None)
        _save_history()
        return True


def shutdown_workers() -> None:
    """Signal the worker threads to stop and wait for them to finish."""
    if not _workers:
        return
    stop_event.set()
    for _ in _workers:
        try:
            _queue.put_nowait(_SENTINEL)
        except Full:
            logging.warning("Shutdown sentinel could not be queued because the queue is full")
    for t in list(_workers):
        t.join(timeout=5)
        if t.is_alive():
            logging.warning("Worker thread %s did not exit in time", t.name)
    _workers.clear()
    global _worker_started
    _worker_started = False
    stop_event.clear()
