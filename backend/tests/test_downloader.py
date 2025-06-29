import sys
import threading
from pathlib import Path
from queue import Queue

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import backend.downloader as downloader  # noqa: E402


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


def test_save_history_ioerror(monkeypatch, caplog, tmp_path):
    import builtins
    import importlib
    import logging

    dl = importlib.reload(downloader)

    monkeypatch.setattr(dl, "_queue", Queue())
    monkeypatch.setattr(dl, "_progress", {})
    monkeypatch.setattr(dl, "_history", {})
    monkeypatch.setattr(dl, "_worker_started", True)
    monkeypatch.setattr(dl, "stop_event", threading.Event())
    monkeypatch.setattr(dl, "_workers", [])
    monkeypatch.setattr(dl, "HISTORY_FILE", str(tmp_path / "history.json"))

    def bad_open(*args, **kwargs):
        raise IOError("boom")

    monkeypatch.setattr(builtins, "open", bad_open)
    with caplog.at_level(logging.ERROR):
        dl._save_history()
        assert "Failed to write history file" in caplog.text


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


def test_shutdown_with_full_queue(monkeypatch, tmp_path):
    q = Queue(maxsize=1)
    q.put(("tid", "http://example.com", "video", str(tmp_path)))

    class DummyDL:
        def __init__(self, opts):
            pass

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            pass

        def download(self, urls):
            pass

    monkeypatch.setattr(downloader, "_queue", q)
    monkeypatch.setattr(downloader.yt_dlp, "YoutubeDL", DummyDL)
    t = threading.Thread(target=downloader._worker)
    t.start()
    monkeypatch.setattr(downloader, "_workers", [t])
    downloader.shutdown_workers()
    t.join(1)
    assert not t.is_alive()
    assert downloader._workers == []
