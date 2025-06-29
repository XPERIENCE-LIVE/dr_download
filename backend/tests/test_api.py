import sys
from pathlib import Path
from unittest.mock import patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from backend import main  # noqa: E402

app = main.app


@pytest_asyncio.fixture
async def client():
    transport = ASGITransport(app=app, raise_app_exceptions=False)
    async with AsyncClient(
        transport=transport,
        base_url="http://testserver",
    ) as client:
        yield client


@pytest.mark.asyncio
async def test_post_download(client, tmp_path):
    with patch("backend.main.enqueue_download", return_value="tid") as enq:
        data = {
            "url": "http://example.com",
            "format": "audio",
            "output_dir": str(tmp_path),
        }
        resp = await client.post("/download/", json=data)
        assert resp.status_code == 200
        assert resp.json() == {"status": "queued", "task_id": "tid"}
        enq.assert_called_with("http://example.com", "audio", str(tmp_path))


@pytest.mark.asyncio
async def test_get_progress_endpoint(client):
    with patch("backend.main.get_progress", return_value=55) as gp:
        resp = await client.get("/progress/abc")
        assert resp.status_code == 200
        assert resp.json() == {"progress": 55}
        gp.assert_called_with("abc")


@pytest.mark.asyncio
async def test_update_config_valid(client):
    with patch("backend.main.save_config") as save:
        data = {"theme": "light", "default_format": "audio"}
        resp = await client.post("/config/", json=data)
        assert resp.status_code == 200
        assert resp.json() == {"status": "ok"}
        save.assert_called_with({"theme": "light", "default_format": "audio"})


@pytest.mark.asyncio
async def test_update_config_invalid_type(client):
    with patch("backend.main.save_config") as save:
        data = {"theme": "light", "default_format": ["invalid"]}
        resp = await client.post("/config/", json=data)
        assert resp.status_code == 422
        save.assert_not_called()


@pytest.mark.asyncio
async def test_update_config_serialization_error(client):
    with patch("backend.main.save_config", side_effect=TypeError("boom")):
        data = {"theme": "dark", "default_format": "video"}
        resp = await client.post("/config/", json=data)
        assert resp.status_code == 500


@pytest.mark.asyncio
async def test_shutdown_endpoint(client):
    with patch("backend.main.shutdown_workers"):
        resp = await client.post("/shutdown/")
        assert resp.status_code == 200
        assert resp.json() == {"status": "stopping"}
