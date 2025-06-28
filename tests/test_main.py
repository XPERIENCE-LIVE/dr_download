import sys
from pathlib import Path
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from unittest.mock import patch

# Ensure backend modules can be imported
backend_path = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(backend_path))

from main import app  # noqa: E402

@pytest_asyncio.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        yield client


@pytest.mark.asyncio
async def test_download_invalid_format(client, tmp_path):
    data = {
        "url": "https://example.com",
        "format": "invalid",
        "output_dir": str(tmp_path),
    }
    response = await client.post("/download/", json=data)
    assert response.status_code == 400
    assert "format" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_download_valid_format(client, tmp_path):
    with patch("main.enqueue_download", return_value="123") as mock_enqueue:
        data = {
            "url": "https://example.com",
            "format": "video",
            "output_dir": str(tmp_path),
        }
        response = await client.post("/download/", json=data)
        assert response.status_code == 200
        assert response.json() == {"status": "queued", "task_id": "123"}
        mock_enqueue.assert_called_with(
            "https://example.com",
            "video",
            str(tmp_path),
        )
