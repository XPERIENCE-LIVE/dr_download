from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from backend import main


@pytest_asyncio.fixture
async def client():
    transport = ASGITransport(app=main.app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://testserver") as value:
        yield value


@pytest.mark.asyncio
async def test_inspect_media_returns_normalized_metadata(client):
    metadata = {
        "title": "Demo",
        "author": "Channel",
        "duration": 90,
        "thumbnail": "https://example.com/thumb.jpg",
        "formats": [{"id": "best", "kind": "video", "label": "Mejor calidad"}],
    }
    with patch("backend.main.inspect_media", return_value=metadata) as inspect:
        response = await client.post(
            "/media/inspect",
            json={"url": "https://youtu.be/example", "cookie_source": "edge"},
        )

    assert response.status_code == 200
    assert response.json() == metadata
    inspect.assert_called_once_with("https://youtu.be/example", "edge")


@pytest.mark.asyncio
async def test_inspect_media_explains_locked_browser_session(client):
    failure = PermissionError("Could not copy Chrome cookie database")
    with patch("backend.main.inspect_media", side_effect=failure):
        response = await client.post(
            "/media/inspect",
            json={"url": "https://youtu.be/example", "cookie_source": "edge"},
        )

    assert response.status_code == 400
    detail = response.json()["detail"]
    assert detail["code"] == "browser_locked"
    assert "Edge" in detail["recovery"]


@pytest.mark.asyncio
async def test_inspect_media_explains_edge_dpapi_session_failure(client):
    with patch(
        "backend.main.inspect_media", side_effect=RuntimeError("Failed to decrypt with DPAPI")
    ):
        response = await client.post(
            "/media/inspect",
            json={"url": "https://youtu.be/example", "cookie_source": "edge"},
        )

    assert response.status_code == 400
    detail = response.json()["detail"]
    assert detail["code"] == "session_required"
    assert "Edge" in detail["recovery"]


@pytest.mark.asyncio
async def test_download_collection_supports_queue_and_detail(client, tmp_path: Path):
    task = {"id": "task-1", "status": "queued", "progress": 0}
    with patch("backend.main.enqueue_premium_download", return_value=task) as enqueue:
        response = await client.post(
            "/downloads",
            json={
                "url": "https://example.com/video",
                "format_id": "audio-mp3",
                "output_dir": str(tmp_path),
                "cookie_source": "none",
            },
        )
    assert response.status_code == 200
    assert response.json() == task
    enqueue.assert_called_once()

    with patch("backend.main.list_downloads", return_value=[task]):
        response = await client.get("/downloads")
    assert response.json() == [task]

    with patch("backend.main.get_download", return_value=task):
        response = await client.get("/downloads/task-1")
    assert response.json() == task


@pytest.mark.asyncio
async def test_create_download_rejects_destination_without_safe_free_space(client, tmp_path):
    with patch("backend.main.shutil.disk_usage", return_value=SimpleNamespace(free=1024)):
        response = await client.post(
            "/downloads",
            json={
                "url": "https://example.com/video",
                "format_id": "audio-mp3",
                "output_dir": str(tmp_path),
                "cookie_source": "none",
            },
        )

    assert response.status_code == 400
    assert response.json()["detail"]["code"] == "disk_full"


@pytest.mark.asyncio
async def test_download_actions_return_actionable_not_found(client):
    with patch("backend.main.cancel_download", return_value=False):
        response = await client.post("/downloads/missing/cancel")
    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "download_not_found"


@pytest.mark.asyncio
async def test_retry_and_delete_download(client):
    retried = {"id": "new-task", "status": "queued", "progress": 0}
    with patch("backend.main.retry_download", return_value=retried):
        response = await client.post("/downloads/old-task/retry")
    assert response.status_code == 200
    assert response.json() == retried

    with patch("backend.main.delete_download", return_value=True):
        response = await client.delete("/downloads/old-task")
    assert response.status_code == 200
    assert response.json() == {"status": "deleted"}


@pytest.mark.asyncio
async def test_session_token_protects_local_api(client, monkeypatch):
    monkeypatch.setattr(main, "SESSION_TOKEN", "secret")
    response = await client.get("/downloads")
    assert response.status_code == 401

    with patch("backend.main.list_downloads", return_value=[]):
        response = await client.get(
            "/downloads", headers={"X-Dr-Download-Token": "secret"}
        )
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_put_config_accepts_premium_preferences(client):
    payload = {
        "theme": "dark",
        "default_format": "video",
        "language": "en",
        "cookie_source": "edge",
        "notifications": False,
        "output_dir": "C:/Downloads",
    }
    with patch("backend.main.save_config") as save:
        response = await client.put("/config", json=payload)
    assert response.status_code == 200
    save.assert_called_once_with(payload)
