import json
import sqlite3

import pytest

from backend.store import DownloadStore


def test_store_round_trips_downloads(tmp_path):
    store = DownloadStore(tmp_path / "downloads.db")
    store.upsert({"id": "one", "status": "queued", "progress": 0, "title": "Demo"})
    store.upsert({"id": "one", "status": "completed", "progress": 100, "title": "Demo"})

    assert store.get("one")["status"] == "completed"
    assert store.list()[0]["progress"] == 100

    store.delete("one")
    assert store.get("one") is None


def test_json_migration_is_idempotent_and_keeps_backup(tmp_path):
    legacy = tmp_path / "history.json"
    legacy.write_text(json.dumps({"old": {"id": "old", "status": "done"}}), encoding="utf-8")
    store = DownloadStore(tmp_path / "downloads.db")

    assert store.migrate_json(legacy) == 1
    assert store.migrate_json(legacy) == 0
    assert store.get("old")["status"] == "completed"
    assert legacy.with_suffix(".json.bak").exists()


def test_history_snapshot_only_writes_changed_rows(tmp_path):
    path = tmp_path / "downloads.db"
    store = DownloadStore(path)
    items = [{"id": str(index), "status": "completed"} for index in range(1000)]
    store.replace_all(items)
    with sqlite3.connect(path) as connection:
        connection.executescript("""
            CREATE TABLE writes (operation TEXT);
            CREATE TRIGGER inserted AFTER INSERT ON downloads
                BEGIN INSERT INTO writes VALUES ('insert'); END;
            CREATE TRIGGER updated AFTER UPDATE ON downloads
                BEGIN INSERT INTO writes VALUES ('update'); END;
            CREATE TRIGGER deleted AFTER DELETE ON downloads
                BEGIN INSERT INTO writes VALUES ('delete'); END;
        """)
    store.replace_all(items)
    with sqlite3.connect(path) as connection:
        assert connection.execute("SELECT COUNT(*) FROM writes").fetchone()[0] == 0

    items[500] = {"id": "500", "status": "failed"}
    store.replace_all(items)
    with sqlite3.connect(path) as connection:
        assert connection.execute("SELECT operation FROM writes").fetchall() == [("update",)]
    assert store.get("500")["status"] == "failed"


def test_history_snapshot_removes_expired_records_and_keeps_newest_first(tmp_path):
    store = DownloadStore(tmp_path / "downloads.db")
    store.replace_all([{"id": "old"}, {"id": "kept"}])
    store.replace_all([{"id": "kept"}, {"id": "new"}])
    assert [item["id"] for item in store.list()] == ["new", "kept"]
    assert store.get("old") is None
    store.replace_all([])
    assert store.list() == []


def test_invalid_history_snapshot_leaves_existing_records_intact(tmp_path):
    store = DownloadStore(tmp_path / "downloads.db")
    store.replace_all([{"id": "kept", "status": "completed"}])
    with pytest.raises(sqlite3.IntegrityError):
        store.replace_all([{"id": "duplicate"}, {"id": "duplicate"}])
    assert store.list() == [{"id": "kept", "status": "completed"}]


def test_history_snapshot_rolls_back_deletions_when_an_update_fails(tmp_path):
    path = tmp_path / "downloads.db"
    store = DownloadStore(path)
    original = [{"id": "old"}, {"id": "blocked", "status": "completed"}]
    store.replace_all(original)
    with sqlite3.connect(path) as connection:
        connection.executescript("""
            CREATE TRIGGER prevent_update BEFORE UPDATE ON downloads
            BEGIN SELECT RAISE(ABORT, 'write rejected'); END;
        """)
    with pytest.raises(sqlite3.IntegrityError, match="write rejected"):
        store.replace_all([{"id": "blocked", "status": "failed"}])
    assert store.get("old") == {"id": "old"}
    assert store.get("blocked") == {"id": "blocked", "status": "completed"}


def test_store_closes_connections_after_each_operation(tmp_path, monkeypatch):
    connections = []
    connect = sqlite3.connect

    class TrackedConnection(sqlite3.Connection):
        closed = False

        def close(self):
            self.closed = True
            super().close()

    def tracked_connect(*args, **kwargs):
        connection = connect(*args, **kwargs, factory=TrackedConnection)
        connections.append(connection)
        return connection

    monkeypatch.setattr(sqlite3, "connect", tracked_connect)
    store = DownloadStore(tmp_path / "downloads.db")
    store.replace_all([{"id": "one"}])
    store.get("one")
    store.list()
    store.delete("one")
    assert connections and all(connection.closed for connection in connections)

