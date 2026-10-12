"""SQLite/API isolation tests; provider acceptance requires the real smoke."""

import importlib
import importlib.util
import json
import sqlite3
import subprocess
import sys
import threading
from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.store import DownloadStore


def test_playlist_api_exists():
    assert importlib.util.find_spec("backend.playlist_routes"), "Playlist API is not implemented"


@pytest.fixture
def playlists(tmp_path, monkeypatch):
    if not importlib.util.find_spec("backend.playlist_routes"):
        pytest.skip("Playlist API is not implemented")
    routes = importlib.import_module("backend.playlist_routes")
    store = DownloadStore(tmp_path / "history.db")
    monkeypatch.setattr(routes, "get_store", lambda: store)
    monkeypatch.setattr(routes, "authorized_cookie_source", lambda source: "none")
    routes.shutdown_imports()
    app = FastAPI()
    app.include_router(routes.router)
    with TestClient(app) as client:
        yield client, store, routes
    routes.shutdown_imports()


def test_playlist_crud_persists_and_preserves_downloads(playlists):
    client, store, _ = playlists
    store.upsert({"id": "download", "status": "completed"})
    created = client.post("/playlists", json={"name": "  Viajes  "})
    assert created.status_code == 200
    playlist = created.json()
    assert playlist["name"] == "Viajes" and playlist["items"] == []
    assert playlist["created_at"]
    assert client.get("/playlists").json() == [playlist]
    renamed = client.put(f'/playlists/{playlist["id"]}', json={"name": "Nueva"})
    assert renamed.json()["name"] == "Nueva"
    assert DownloadStore(store.path).list_playlists()[0]["name"] == "Nueva"
    assert client.delete(f'/playlists/{playlist["id"]}').status_code == 204
    assert client.get("/playlists").json() == []
    assert store.get("download") == {"id": "download", "status": "completed"}


def test_playlist_items_keep_order_allow_duplicates_and_cascade(playlists):
    client, store, _ = playlists
    playlist_id = client.post("/playlists", json={"name": "List"}).json()["id"]
    path = f"/playlists/{playlist_id}/items"
    body = {"url": "https://www.youtube.com/watch?v=BaW_jenozKc", "title": "Demo", "duration": 9.25}
    first = client.post(path, json=body).json()
    second = client.post(path, json=body).json()
    assert first["duplicate"] is False and second["duplicate"] is True
    assert first["id"] != second["id"]
    items = client.get("/playlists").json()[0]["items"]
    assert [item["id"] for item in items] == [first["id"], second["id"]]
    assert items[0]["duration"] == 9.25 and items[0]["available"] is True
    assert client.delete(f'{path}/{first["id"]}').status_code == 204
    assert len(client.get("/playlists").json()[0]["items"]) == 1
    client.delete(f"/playlists/{playlist_id}")
    with sqlite3.connect(store.path) as connection:
        assert connection.execute("SELECT COUNT(*) FROM playlist_items").fetchone()[0] == 0


@pytest.mark.parametrize("name", ["", "   ", "x" * 101, 32, None])
def test_invalid_playlist_name_is_rejected(playlists, name):
    client, _, _ = playlists
    assert client.post("/playlists", json={"name": name}).status_code in {400, 422}
    assert client.get("/playlists").json() == []


@pytest.mark.parametrize("url", ["http://youtube.com/watch?v=a", "https://youtube.com.evil.test/a", "https://user:pass@youtube.com/a", "https://@youtube.com/a", "https://127.0.0.1/a", "file:///tmp/video", "https://youtube.com:444/a", "https://youtu.be/a\n", "https://youtu.be/a#fragment", "https://youtu.be/a\x7f"])
def test_playlist_rejects_non_provider_urls(playlists, url):
    client, _, _ = playlists
    playlist_id = client.post("/playlists", json={"name": "List"}).json()["id"]
    assert client.post(f"/playlists/{playlist_id}/items", json={"url": url}).status_code in {400, 422}
    assert client.get("/playlists").json()[0]["items"] == []


def test_playlist_metadata_is_bounded_and_safe(playlists):
    client, _, _ = playlists
    playlist_id = client.post("/playlists", json={"name": "List"}).json()["id"]
    path = f"/playlists/{playlist_id}/items"
    assert client.post(path, json={"url": "https://youtu.be/a", "duration": -1}).status_code in {400, 422}
    assert client.post(path, json={"url": "https://youtu.be/a", "duration": True}).status_code in {400, 422}
    item = client.post(path, json={"url": "https://youtu.be/a", "title": "x" * 10000, "thumbnail": "https://evil.test/a?token=secret", "stream_url": "https://evil.test/signed"}).json()
    assert len(item["title"]) <= 500
    assert item["thumbnail"] is None
    assert "stream_url" not in item and "secret" not in json.dumps(client.get("/playlists").json())


def test_playlist_missing_resources_and_storage_failure_are_visible(playlists, monkeypatch):
    client, store, _ = playlists
    unknown = str(uuid4())
    assert client.put(f"/playlists/{unknown}", json={"name": "Missing"}).status_code == 404
    assert client.post(f"/playlists/{unknown}/items", json={"url": "https://youtu.be/a"}).status_code == 404
    def fail():
        raise sqlite3.OperationalError("database locked secret")
    monkeypatch.setattr(store, "list_playlists", fail)
    response = client.get("/playlists")
    assert response.status_code == 503
    assert response.json()["detail"]["code"] == "playlist_storage_unavailable"
    assert "secret" not in response.text


def test_import_preserves_unavailable_entries_and_safe_metadata(playlists, monkeypatch):
    client, _, routes = playlists
    monkeypatch.setattr(routes, "_extract_playlist", lambda *args: {
        "title": "  My source  ", "entries": [
            {"id": "BaW_jenozKc", "url": "https://www.youtube.com/watch?v=BaW_jenozKc", "title": "First", "duration": 5},
            {"id": "missing1234", "url": "https://www.youtube.com/watch?v=missing1234", "title": "[Private video]", "availability": "private"},
            None,
        ],
    })
    response = client.post("/playlists/import", json={"request_id": str(uuid4()), "url": "https://youtube.com/playlist?list=PL1"})
    assert response.status_code == 200, response.text
    result = response.json()
    assert result["imported"] == 3 and result["unavailable"] == 2
    assert result["playlist"]["name"] == "My source"
    assert [item["available"] for item in result["playlist"]["items"]] == [True, False, False]
    assert client.get("/playlists").json() == [result["playlist"]]


@pytest.mark.parametrize("payload", [{"entries": [{"id": "a"}] * 501}, {"entries": [{"id": "a"}], "playlist_count": 501}])
def test_import_over_500_rolls_back_everything(playlists, monkeypatch, payload):
    client, _, routes = playlists
    monkeypatch.setattr(routes, "_extract_playlist", lambda *args: payload)
    response = client.post("/playlists/import", json={"request_id": str(uuid4()), "url": "https://youtube.com/playlist?list=PL1"})
    assert response.status_code == 400
    assert response.json()["detail"]["code"] == "playlist_too_large"
    assert client.get("/playlists").json() == []


def test_import_requires_persisted_cookie_consent(playlists, monkeypatch):
    client, _, routes = playlists
    def unexpected(*args):
        pytest.fail("Extractor accessed cookies before authorization")
    monkeypatch.setattr(routes, "_extract_playlist", unexpected)
    response = client.post("/playlists/import", json={"request_id": str(uuid4()), "url": "https://youtube.com/playlist?list=PL1", "cookie_source": "edge"})
    assert response.status_code == 403
    assert response.json()["detail"]["code"] == "browser_consent_required"


def test_cancel_import_before_start_is_idempotent_and_prevents_commit(playlists, monkeypatch):
    client, _, routes = playlists
    request_id = str(uuid4())
    monkeypatch.setattr(routes, "_extract_playlist", lambda *args: {"entries": []})
    assert client.delete(f"/playlists/import/{request_id}").status_code == 204
    assert client.delete(f"/playlists/import/{request_id}").status_code == 204
    response = client.post("/playlists/import", json={"request_id": request_id, "url": "https://youtube.com/playlist?list=PL1"})
    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "playlist_import_cancelled"
    assert client.get("/playlists").json() == []


def test_cancel_import_just_before_commit_is_atomic(playlists, monkeypatch):
    client, _, routes = playlists
    request_id = str(uuid4())
    extracted, resume = threading.Event(), threading.Event()
    def extract(*args):
        extracted.set()
        assert resume.wait(5)
        return {"title": "Cancelled", "entries": [{"id": "BaW_jenozKc"}]}
    monkeypatch.setattr(routes, "_extract_playlist", extract)
    with ThreadPoolExecutor() as executor:
        future = executor.submit(client.post, "/playlists/import", json={"request_id": request_id, "url": "https://youtube.com/playlist?list=PL1"})
        assert extracted.wait(5)
        assert client.delete(f"/playlists/import/{request_id}").status_code == 204
        resume.set()
        response = future.result(timeout=5)
    assert response.status_code == 409
    assert client.get("/playlists").json() == []


def test_import_sqlite_failure_rolls_back_entire_playlist(playlists, monkeypatch):
    client, store, routes = playlists
    with sqlite3.connect(store.path) as connection:
        connection.executescript("CREATE TRIGGER reject_item BEFORE INSERT ON playlist_items BEGIN SELECT RAISE(ABORT, 'write rejected'); END;")
    monkeypatch.setattr(routes, "_extract_playlist", lambda *args: {"title": "Broken", "entries": [{"id": "BaW_jenozKc"}]})
    response = client.post("/playlists/import", json={"request_id": str(uuid4()), "url": "https://youtube.com/playlist?list=PL1"})
    assert response.status_code == 503
    assert client.get("/playlists").json() == []


def test_revoked_cookie_consent_before_commit_prevents_import(playlists, monkeypatch):
    client, _, routes = playlists
    consent = {"source": "edge"}
    monkeypatch.setattr(routes, "authorized_cookie_source", lambda source: consent["source"])
    def extract(*args):
        consent["source"] = "none"
        return {"title": "Revoked", "entries": [{"id": "BaW_jenozKc"}]}
    monkeypatch.setattr(routes, "_extract_playlist", extract)
    response = client.post("/playlists/import", json={"request_id": str(uuid4()), "url": "https://youtube.com/playlist?list=PL1", "cookie_source": "edge"})
    assert response.status_code == 403
    assert client.get("/playlists").json() == []


@pytest.mark.parametrize("url", ["https://youtu.be/BaW_jenozKc", "https://player.vimeo.com/video/123", "https://m.youtube.com/watch?v=a"])
def test_known_provider_subdomains_are_supported(playlists, url):
    client, _, _ = playlists
    playlist_id = client.post("/playlists", json={"name": "List"}).json()["id"]
    response = client.post(f"/playlists/{playlist_id}/items", json={"url": url})
    assert response.status_code == 200 and response.json()["url"] == url


def test_import_reuses_request_id_without_duplicate_commit(playlists, monkeypatch):
    client, _, routes = playlists
    monkeypatch.setattr(routes, "_extract_playlist", lambda *args: {"title": "Imported", "entries": []})
    body = {"request_id": str(uuid4()), "url": "https://youtube.com/playlist?list=PL1"}
    assert client.post("/playlists/import", json=body).status_code == 200
    assert client.post("/playlists/import", json=body).status_code == 409
    assert len(client.get("/playlists").json()) == 1


def test_cancel_already_committed_import_reports_completion_without_removing_it(playlists, monkeypatch):
    client, _, routes = playlists
    monkeypatch.setattr(routes, "_extract_playlist", lambda *args: {"title": "Imported", "entries": []})
    request_id = str(uuid4())
    response = client.post("/playlists/import", json={"request_id": request_id, "url": "https://youtube.com/playlist?list=PL1"})
    assert response.status_code == 200
    for _ in range(2):
        cancellation = client.delete(f"/playlists/import/{request_id}")
        assert cancellation.status_code == 409
        assert cancellation.json()["detail"]["code"] == "playlist_import_completed"
    assert client.get("/playlists").json() == [response.json()["playlist"]]


def _python_engine(monkeypatch, routes, program):
    """Real OS child process with controlled metadata; not provider acceptance."""
    original = subprocess.Popen
    processes, commands, started = [], [], threading.Event()
    def spawn(command, **kwargs):
        if command[0] != "included-yt-dlp.exe":
            return original(command, **kwargs)
        commands.append(command)
        process = original([sys.executable, "-c", program], **kwargs)
        processes.append(process)
        started.set()
        return process
    monkeypatch.setattr(routes, "resolve_engine", lambda: "included-yt-dlp.exe")
    monkeypatch.setattr(routes, "node_runtime_argument", lambda: "node:included-node.exe")
    monkeypatch.setattr(routes.subprocess, "Popen", spawn)
    return processes, commands, started


def test_import_engine_protocol_reads_json_and_closes_real_process_pipes(playlists, monkeypatch):
    client, _, routes = playlists
    processes, commands, _ = _python_engine(monkeypatch, routes, 'print(\'{"title":"Engine","entries":[{"id":"BaW_jenozKc","title":"First"}]}\')')
    response = client.post("/playlists/import", json={"request_id": str(uuid4()), "url": "https://youtube.com/playlist?list=PL1"})
    assert response.status_code == 200, response.text
    assert response.json()["playlist"]["items"][0]["url"] == "https://www.youtube.com/watch?v=BaW_jenozKc"
    assert processes[0].poll() == 0
    assert processes[0].stdout.closed and processes[0].stderr.closed
    assert commands[0][:7] == ["included-yt-dlp.exe", "--ignore-config", "--no-warnings", "--flat-playlist", "--dump-single-json", "--playlist-end", "501"]
    assert "--ignore-errors" in commands[0] and "--cookies-from-browser" not in commands[0]
    assert commands[0][-2:] == ["--", "https://youtube.com/playlist?list=PL1"]


def test_cancel_import_terminates_real_owned_child_and_closes_pipes(playlists, monkeypatch):
    client, _, routes = playlists
    processes, _, started = _python_engine(monkeypatch, routes, "import time; time.sleep(60)")
    request_id = str(uuid4())
    with ThreadPoolExecutor() as executor:
        future = executor.submit(client.post, "/playlists/import", json={"request_id": request_id, "url": "https://youtube.com/playlist?list=PL1"})
        assert started.wait(5)
        response = client.delete(f"/playlists/import/{request_id}")
        assert response.status_code == 204
        result = future.result(timeout=15)
    assert result.status_code == 409
    assert processes[0].poll() is not None
    assert processes[0].stdout.closed and processes[0].stderr.closed
    assert client.get("/playlists").json() == []


def test_import_invalid_output_does_not_leak_stderr_or_commit(playlists, monkeypatch):
    client, _, routes = playlists
    processes, _, _ = _python_engine(monkeypatch, routes, 'import sys; print("https://provider.test/signed?token=secret", file=sys.stderr); print("not json")')
    response = client.post("/playlists/import", json={"request_id": str(uuid4()), "url": "https://vimeo.com/showcase/123"})
    assert response.status_code == 400
    assert "secret" not in response.text and "provider.test" not in response.text
    assert processes[0].stdout.closed and processes[0].stderr.closed
    assert client.get("/playlists").json() == []


def test_import_bounds_real_child_output_and_cleans_it_up(playlists, monkeypatch):
    client, _, routes = playlists
    processes, _, _ = _python_engine(monkeypatch, routes, 'import sys,time; sys.stdout.write("x" * (9 * 1024 * 1024)); sys.stdout.flush(); time.sleep(60)')
    response = client.post("/playlists/import", json={"request_id": str(uuid4()), "url": "https://vimeo.com/showcase/123"})
    assert response.status_code == 400
    assert processes[0].poll() is not None
    assert processes[0].stdout.closed and processes[0].stderr.closed
    assert client.get("/playlists").json() == []


def test_import_exactly_500_entries_succeeds_atomically(playlists, monkeypatch):
    client, _, routes = playlists
    monkeypatch.setattr(routes, "_extract_playlist", lambda *args: {"title": "Limit", "entries": [{"id": f"video_{i}", "title": f"Video {i}"} for i in range(500)]})
    response = client.post("/playlists/import", json={"request_id": str(uuid4()), "url": "https://youtube.com/playlist?list=PL1"})
    assert response.status_code == 200, response.text
    assert response.json()["imported"] == 500 and response.json()["unavailable"] == 0
    assert len(client.get("/playlists").json()[0]["items"]) == 500


def test_playlist_list_is_consistent_during_concurrent_delete(tmp_path, monkeypatch):
    store = DownloadStore(tmp_path / "history.db")
    original = store.create_playlist("Snapshot")
    with sqlite3.connect(store.path) as connection:
        connection.execute("PRAGMA journal_mode=WAL")
    read_playlist = store._playlist
    def delete_then_read(connection, playlist_id):
        DownloadStore(store.path).delete_playlist(playlist_id)
        return read_playlist(connection, playlist_id)
    monkeypatch.setattr(store, "_playlist", delete_then_read)
    assert store.list_playlists() == [original]
    assert DownloadStore(store.path).list_playlists() == []
