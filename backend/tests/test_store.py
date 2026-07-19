import json

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

