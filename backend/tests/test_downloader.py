import sys
import threading
from pathlib import Path
from queue import Queue

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import backend.downloader as downloader  # noqa: E402

_real_save_history = downloader._save_history


@pytest.fixture(autouse=True)
def reset_state(monkeypatch):
    monkeypatch.setattr(downloader, "_queue", Queue())
    monkeypatch.setattr(downloader, "_progress", {})
    monkeypatch.setattr(downloader, "_history", {})
    monkeypatch.setattr(downloader, "_worker_started", True)
    monkeypatch.setattr(downloader, "stop_event", threading.Event())
    monkeypatch.setattr(downloader, "_workers", [])
    monkeypatch.setattr(downloader, "_save_history", lambda: None)
    yield


def test_enqueue_download(tmp_path):
    task_id = downloader.enqueue_download(
        "http://example.com",
        "video",
        str(tmp_path),
    )
    assert task_id in downloader._progress
    assert task_id in downloader._history
    queued = downloader._queue.get_nowait()
    assert queued[0] == task_id
    entry = downloader._history[task_id]
    assert entry["status"] == "queued"
    assert entry["url"] == "http://example.com"


def test_retry_download_reuses_id_without_duplicate_history(tmp_path):
    downloader._history["task-1"] = {
        "id": "task-1",
        "url": "https://example.com/video",
        "format": "audio",
        "format_id": "audio-mp3",
        "output_dir": str(tmp_path),
        "cookie_source": "none",
        "status": "failed",
        "error": {"code": "network_error"},
    }

    retried = downloader.retry_download("task-1")

    assert retried["id"] == "task-1"
    assert retried["status"] == "queued"
    assert list(downloader._history) == ["task-1"]
    assert downloader._queue.get_nowait()[0] == "task-1"
    assert "error" not in downloader._history["task-1"]


def test_delete_download_preserves_completed_file(tmp_path):
    output = tmp_path / "finished.mp3"
    output.write_bytes(b"audio")
    downloader._history["task-1"] = {
        "id": "task-1",
        "status": "completed",
        "filename": str(output),
        "output_dir": str(tmp_path),
    }

    assert downloader.delete_download("task-1") is True
    assert output.read_bytes() == b"audio"
    assert "task-1" not in downloader._history


def test_get_progress(tmp_path):
    downloader._progress["abc"] = 25
    assert downloader.get_progress("abc") == 25
    downloader._progress.clear()
    downloader._history["abc"] = {"status": "done"}
    assert downloader.get_progress("abc") == 100
    assert downloader.get_progress("missing") == 0


def test_worker_handles_queue_get_failure(monkeypatch):
    class BadQueue:
        def __init__(self):
            self.calls = 0

        def get(self, timeout=None):
            self.calls += 1
            if self.calls == 1:
                raise Exception("boom")
            raise SystemExit()

        def task_done(self):
            raise RuntimeError("task_done called")

    monkeypatch.setattr(downloader, "_queue", BadQueue())

    with pytest.raises(SystemExit):
        downloader._worker()


def test_shutdown_workers_sends_sentinel(monkeypatch):
    puts = []

    class DummyQueue(Queue):
        def put_nowait(self, item):
            puts.append(item)

    monkeypatch.setattr(downloader, "_queue", DummyQueue())
    t1 = threading.Thread(target=lambda: None)
    t2 = threading.Thread(target=lambda: None)
    t1.start()
    t2.start()
    monkeypatch.setattr(downloader, "_workers", [t1, t2])
    downloader.shutdown_workers()
    assert puts == [downloader._SENTINEL, downloader._SENTINEL]
    assert downloader._workers == []


def test_save_history_uses_sqlite_without_writing_legacy_json(monkeypatch):
    import builtins
    import importlib

    dl = importlib.reload(downloader)

    monkeypatch.setattr(dl, "_queue", Queue())
    monkeypatch.setattr(dl, "_progress", {})
    monkeypatch.setattr(dl, "_history", {})
    monkeypatch.setattr(dl, "_worker_started", True)
    monkeypatch.setattr(dl, "stop_event", threading.Event())
    monkeypatch.setattr(dl, "_workers", [])
    opened = []
    monkeypatch.setattr(builtins, "open", lambda *args, **kwargs: opened.append(args))

    dl._save_history()

    assert opened == []


def test_save_history_truncates(monkeypatch, tmp_path):
    import importlib

    dl = importlib.reload(downloader)

    monkeypatch.setattr(dl, "_queue", Queue())
    monkeypatch.setattr(dl, "_progress", {})
    # pre-populate history with more entries than the limit
    history = {
        f"t{i}": {"id": f"t{i}", "status": "done"}
        for i in range(dl._MAX_HISTORY_LEN + 5)
    }
    monkeypatch.setattr(dl, "_history", history)
    monkeypatch.setattr(dl, "_worker_started", True)
    monkeypatch.setattr(dl, "stop_event", threading.Event())
    monkeypatch.setattr(dl, "_workers", [])
    monkeypatch.setattr(dl, "HISTORY_FILE", str(tmp_path / "history.json"))

    dl._save_history()

    assert len(dl._history) == dl._MAX_HISTORY_LEN
    # oldest entries should have been removed
    assert "t0" not in dl._history


def test_worker_consumes_sentinel_when_stopping(monkeypatch):
    q = Queue()
    q.put(downloader._SENTINEL)
    monkeypatch.setattr(downloader, "_queue", q)
    downloader.stop_event.set()
    downloader._worker()
    assert q.empty()


def test_worker_uses_only_the_resolved_external_engine(monkeypatch, tmp_path):
    observed = {}
    q = Queue()
    q.put(("tid", "https://example.com", "video", str(tmp_path), "video-best", "none"))

    def download(engine, url, format_id, output_dir, cookie_source, on_progress, cancelled):
        observed.update(engine=engine, format_id=format_id, cookie_source=cookie_source)
        downloader.stop_event.set()
        return None

    monkeypatch.setattr(downloader, "_queue", q)
    monkeypatch.setattr(downloader, "resolve_engine", lambda: "C:/engine/yt-dlp.exe")
    monkeypatch.setattr(downloader, "download_with_engine", download)

    downloader._worker()

    assert observed == {
        "engine": "C:/engine/yt-dlp.exe",
        "format_id": "video-best",
        "cookie_source": "none",
    }


def test_shutdown_with_full_queue(monkeypatch, tmp_path):
    q = Queue(maxsize=1)
    q.put(("tid", "http://example.com", "video", str(tmp_path), "video-best", "none"))

    def download(*_args):
        return None

    monkeypatch.setattr(downloader, "_queue", q)
    monkeypatch.setattr(downloader, "resolve_engine", lambda: "C:/engine/yt-dlp.exe")
    monkeypatch.setattr(downloader, "download_with_engine", download)
    t = threading.Thread(target=downloader._worker)
    t.start()
    monkeypatch.setattr(downloader, "_workers", [t])
    downloader.shutdown_workers()
    t.join(1)
    assert not t.is_alive()
    assert downloader._workers == []


def test_worker_records_postprocessed_filename(monkeypatch, tmp_path):
    final_file = tmp_path / "final.mp3"
    q = Queue()
    q.put(("tid", "https://example.com", "audio", str(tmp_path), "audio-mp3", "none"))

    def download(*_args):
        downloader.stop_event.set()
        return str(final_file)

    monkeypatch.setattr(downloader, "_queue", q)
    monkeypatch.setattr(downloader, "resolve_engine", lambda: "C:/engine/yt-dlp.exe")
    monkeypatch.setattr(downloader, "download_with_engine", download)

    downloader._worker()

    assert downloader._history["tid"]["filename"] == str(final_file)


def test_recover_loaded_history_requeues_waiting_and_marks_active_interrupted(tmp_path):
    records = {
        "queued": {
            "id": "queued",
            "url": "https://example.com/queued",
            "format": "audio",
            "format_id": "audio-mp3",
            "output_dir": str(tmp_path),
            "cookie_source": "none",
            "status": "queued",
            "progress": 0,
        },
        "active": {
            "id": "active",
            "url": "https://example.com/active",
            "format": "video",
            "format_id": "video-best",
            "output_dir": str(tmp_path),
            "cookie_source": "none",
            "status": "downloading",
            "progress": 42,
        },
    }

    recovered, waiting = downloader._recover_loaded_history(records)

    assert waiting == [
        (
            "queued",
            "https://example.com/queued",
            "audio",
            str(tmp_path),
            "audio-mp3",
            "none",
        )
    ]
    assert recovered["active"]["status"] == "failed"
    assert recovered["active"]["error"]["code"] == "interrupted"


def test_load_history_applies_recovery_and_restores_waiting_queue(monkeypatch, tmp_path):
    records = [
        {
            "id": "queued",
            "url": "https://example.com/queued",
            "format": "audio",
            "format_id": "audio-mp3",
            "output_dir": str(tmp_path),
            "cookie_source": "none",
            "status": "queued",
            "progress": 0,
        },
        {
            "id": "active",
            "url": "https://example.com/active",
            "format": "video",
            "format_id": "video-best",
            "output_dir": str(tmp_path),
            "cookie_source": "none",
            "status": "postprocessing",
            "progress": 99,
        },
    ]

    class Store:
        def migrate_json(self, path):
            pass

        def list(self):
            return records

    q = Queue()
    monkeypatch.setattr(downloader, "_store", Store())
    monkeypatch.setattr(downloader, "_queue", q)
    monkeypatch.setattr(downloader, "_history", {})
    monkeypatch.setattr(downloader, "HISTORY_FILE", str(tmp_path / "missing.json"))

    downloader._load_history()

    assert downloader._history["active"]["status"] == "failed"
    assert q.get_nowait()[0] == "queued"


def test_load_history_fails_closed_when_sqlite_cannot_be_read(monkeypatch, tmp_path):
    class BrokenStore:
        def migrate_json(self, path):
            raise OSError("database unavailable")

    monkeypatch.setattr(downloader, "_store", BrokenStore())
    monkeypatch.setattr(downloader, "HISTORY_FILE", str(tmp_path / "missing.json"))

    with pytest.raises(OSError, match="database unavailable"):
        downloader._load_history()


def test_save_history_fails_closed_when_sqlite_cannot_be_written(monkeypatch):
    class BrokenStore:
        def replace_all(self, records):
            raise OSError("database is read-only")

    monkeypatch.setattr(downloader, "_store", BrokenStore())

    with pytest.raises(OSError, match="database is read-only"):
        _real_save_history()


def test_worker_enters_inspecting_before_starting_external_engine(monkeypatch, tmp_path):
    q = Queue()
    q.put(("tid", "https://example.com", "audio", str(tmp_path), "audio-mp3", "none"))
    downloader._history["tid"] = {"id": "tid", "status": "queued", "progress": 0}
    observed = []

    def download(*args, **kwargs):
        observed.append(downloader._history["tid"]["status"])
        downloader.stop_event.set()
        return str(tmp_path / "done.mp3")

    monkeypatch.setattr(downloader, "_queue", q)
    monkeypatch.setattr(downloader, "resolve_engine", lambda: "yt-dlp.exe")
    monkeypatch.setattr(downloader, "download_with_engine", download)

    downloader._worker()

    assert observed == ["inspecting"]


def test_start_download_workers_starts_recovered_queue_once(monkeypatch):
    started = []

    class DummyThread:
        def __init__(self, target, daemon):
            self.target = target
            self.daemon = daemon

        def start(self):
            started.append(self)

    monkeypatch.setattr(downloader, "_worker_started", False)
    monkeypatch.setattr(downloader, "_workers", [])
    monkeypatch.setattr(downloader.threading, "Thread", DummyThread)
    monkeypatch.setattr(downloader, "load_config", lambda: {"worker_threads": 1})

    downloader.start_download_workers()
    downloader.start_download_workers()

    assert len(started) == 1
    assert downloader._worker_started is True


def test_worker_persists_structured_engine_error(monkeypatch, tmp_path):
    q = Queue()
    q.put(("tid", "https://example.com", "audio", str(tmp_path), "audio-mp3", "edge"))
    downloader._history["tid"] = {"id": "tid", "status": "queued", "progress": 0}

    def download(*args, **kwargs):
        downloader.stop_event.set()
        raise RuntimeError("Failed to decrypt with DPAPI")

    monkeypatch.setattr(downloader, "_queue", q)
    monkeypatch.setattr(downloader, "resolve_engine", lambda: "yt-dlp.exe")
    monkeypatch.setattr(downloader, "download_with_engine", download)

    downloader._worker()

    assert downloader._history["tid"]["status"] == "failed"
    assert downloader._history["tid"]["error"]["code"] == "session_required"


def test_worker_logs_do_not_expose_urls_or_private_paths(monkeypatch, caplog, tmp_path):
    secret_url = "https://example.com/video?token=secret-value"
    private_path = "C:/Users/Private/Profile/cookies.db"
    q = Queue()
    q.put(("tid", secret_url, "audio", str(tmp_path), "audio-mp3", "none"))
    downloader._history["tid"] = {"id": "tid", "status": "queued", "progress": 0}

    def download(*args, **kwargs):
        downloader.stop_event.set()
        raise RuntimeError(f"engine failed near {private_path}")

    monkeypatch.setattr(downloader, "_queue", q)
    monkeypatch.setattr(downloader, "resolve_engine", lambda: "yt-dlp.exe")
    monkeypatch.setattr(downloader, "download_with_engine", download)

    downloader._worker()

    assert secret_url not in caplog.text
    assert private_path not in caplog.text
