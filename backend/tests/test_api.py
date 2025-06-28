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
