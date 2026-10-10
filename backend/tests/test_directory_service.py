from pathlib import Path

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from unittest.mock import patch

from backend import main
from backend.directory_service import DirectoryCheck, ensure_output_directory


@pytest_asyncio.fixture
async def client():
    async with AsyncClient(
        transport=ASGITransport(app=main.app, raise_app_exceptions=False),
        base_url="http://testserver",
    ) as value:
        yield value


def test_ensure_output_directory_creates_missing_directory(tmp_path: Path):
    target = tmp_path / "nested" / "downloads"

    result = ensure_output_directory(target)

    assert isinstance(result, DirectoryCheck)
    assert result.path == str(target.resolve())
    assert result.exists is True
    assert result.created is True
    assert result.writable is True
    assert result.error is None


def test_ensure_output_directory_rejects_existing_file(tmp_path: Path):
    target = tmp_path / "not-a-directory"
    target.write_text("x", encoding="utf-8")

    result = ensure_output_directory(target)

    assert result.exists is True
    assert result.writable is False
    assert result.error == "not_a_directory"


def test_ensure_output_directory_enforces_free_space(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(
        "backend.directory_service.shutil.disk_usage",
        lambda _path: type("Usage", (), {"free": 10})(),
    )

    result = ensure_output_directory(tmp_path, min_free_bytes=128)

    assert result.writable is False
    assert result.error == "disk_full"


def test_directory_check_exposes_public_contract(tmp_path: Path):
    result = ensure_output_directory(tmp_path / "contract")
    payload = result.as_dict()
    assert payload["accepted"] is True
    assert payload["error_code"] is None
    assert payload["recovery"] == ""


def test_relative_path_is_rejected():
    result = ensure_output_directory("relative-downloads")
    assert result.valid is False
    assert result.error == "invalid_path"


@pytest.mark.asyncio
async def test_validate_directory_endpoint_creates_directory(client, tmp_path: Path):
    target = tmp_path / "new-downloads"
    response = await client.post("/directories/validate", json={"path": str(target)})

    assert response.status_code == 200
    assert response.json()["valid"] is True
    assert target.is_dir()


@pytest.mark.asyncio
async def test_create_download_creates_missing_output_directory(client, tmp_path: Path):
    target = tmp_path / "created-by-download"
    task = {"id": "task-1", "status": "queued", "progress": 0}
    with patch("backend.main.enqueue_premium_download", return_value=task):
        response = await client.post(
            "/downloads",
            json={
                "url": "https://example.com/video",
                "format_id": "audio-mp3",
                "output_dir": str(target),
                "cookie_source": "none",
            },
        )

    assert response.status_code == 200
    assert target.is_dir()


@pytest.mark.asyncio
async def test_create_download_returns_structured_directory_error(client):
    response = await client.post(
        "/downloads",
        json={
            "url": "https://example.com/video",
            "format_id": "audio-mp3",
            "output_dir": "relative-downloads",
            "cookie_source": "none",
        },
    )
    assert response.status_code == 400
    assert response.json()["detail"]["error_code"] == "invalid_path"
