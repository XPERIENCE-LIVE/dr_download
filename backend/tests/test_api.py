import sys
from pathlib import Path
from unittest.mock import patch
from fastapi.testclient import TestClient

backend_path = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_path))

from main import app  # noqa: E402

client = TestClient(app)


def test_post_download(tmp_path):
    with patch("main.enqueue_download", return_value="tid") as enq:
        data = {
            "url": "http://example.com",
            "format": "audio",
            "output_dir": str(tmp_path),
        }
        resp = client.post("/download/", json=data)
        assert resp.status_code == 200
        assert resp.json() == {"status": "queued", "task_id": "tid"}
        enq.assert_called_with("http://example.com", "audio", str(tmp_path))


def test_get_progress_endpoint():
    with patch("main.get_progress", return_value=55) as gp:
        resp = client.get("/progress/abc")
        assert resp.status_code == 200
        assert resp.json() == {"progress": 55}
        gp.assert_called_with("abc")


def test_update_config_valid():
    with patch("main.save_config") as save:
        data = {"theme": "light", "default_format": "audio"}
        resp = client.post("/config/", json=data)
        assert resp.status_code == 200
        assert resp.json() == {"status": "ok"}
        save.assert_called_with({"theme": "light", "default_format": "audio"})


def test_update_config_invalid_type():
    with patch("main.save_config") as save:
        data = {"theme": "light", "default_format": ["invalid"]}
        resp = client.post("/config/", json=data)
        assert resp.status_code == 400
        save.assert_not_called()


def test_update_config_serialization_error():
    with patch("main.save_config", side_effect=TypeError("boom")):
        data = {"theme": "dark", "default_format": "video"}
        resp = client.post("/config/", json=data)
        assert resp.status_code == 400
