from queue import Queue
import threading

import pytest
import sys
from pathlib import Path

backend_path = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_path))

import backend.downloader as downloader


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
        "http://example.com", "video", str(tmp_path)
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
        def put(self, item):
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


