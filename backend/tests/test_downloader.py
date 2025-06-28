from queue import Queue

import pytest

import backend.downloader as downloader


@pytest.fixture(autouse=True)
def reset_state(monkeypatch):
    monkeypatch.setattr(downloader, "_queue", Queue())
    monkeypatch.setattr(downloader, "_progress", {})
    monkeypatch.setattr(downloader, "_history", {})
    monkeypatch.setattr(downloader, "_worker_started", True)
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

        def get(self):
            self.calls += 1
            if self.calls == 1:
                raise Exception("boom")
            raise SystemExit()

        def task_done(self):
            raise RuntimeError("task_done called")

    monkeypatch.setattr(downloader, "_queue", BadQueue())

    with pytest.raises(SystemExit):
        downloader._worker()
