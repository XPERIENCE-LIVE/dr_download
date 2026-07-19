import subprocess
import threading
from unittest.mock import patch

import pytest

from backend.engine_runner import (
    _terminate_process_tree,
    build_command,
    download_with_engine,
    inspect_with_engine,
    node_runtime_argument,
    parse_progress,
    resolve_engine,
)


def test_windows_cancellation_terminates_the_process_tree():
    process = type("Process", (), {"pid": 4321, "wait": lambda self, timeout=None: 0})()

    with patch("backend.engine_runner.os.name", "nt"), patch(
        "backend.engine_runner.subprocess.run"
    ) as run:
        _terminate_process_tree(process)

    assert run.call_args.args[0] == ["taskkill", "/PID", "4321", "/T", "/F"]
    assert run.call_args.kwargs["shell"] is False


def test_build_command_uses_browser_only_when_consented(tmp_path, monkeypatch):
    node = tmp_path / "node.exe"
    node.write_bytes(b"node")
    monkeypatch.setenv("DR_DOWNLOAD_NODE", str(node))
    command = build_command(
        "C:/engine/yt-dlp.exe",
        "https://example.com/video",
        "audio-mp3",
        str(tmp_path),
        "edge",
    )
    assert command[0].endswith("yt-dlp.exe")
    assert command[command.index("--cookies-from-browser") + 1] == "edge"
    assert "--extract-audio" in command

    command = build_command("yt-dlp", "https://example.com", "video-best", str(tmp_path), "none")
    assert "--cookies-from-browser" not in command


def test_build_command_uses_bundled_node_runtime(monkeypatch, tmp_path):
    node = tmp_path / "node.exe"
    node.write_bytes(b"node")
    monkeypatch.setenv("DR_DOWNLOAD_NODE", str(node))

    command = build_command(
        "C:/engine/yt-dlp.exe",
        "https://example.com/video",
        "video-best",
        str(tmp_path),
        "none",
    )

    assert command[command.index("--js-runtimes") + 1] == f"node:{node}"


def test_build_command_rejects_unknown_format(monkeypatch, tmp_path):
    node = tmp_path / "node.exe"
    node.write_bytes(b"node")
    monkeypatch.setenv("DR_DOWNLOAD_NODE", str(node))

    with pytest.raises(ValueError, match="Unsupported format"):
        build_command("yt-dlp.exe", "https://example.com", "unknown", str(tmp_path), "none")


def test_build_command_uses_bundled_ffmpeg(monkeypatch, tmp_path):
    node = tmp_path / "node.exe"
    node.write_bytes(b"node")
    ffmpeg = tmp_path / "ffmpeg"
    ffmpeg.mkdir()
    monkeypatch.setenv("DR_DOWNLOAD_NODE", str(node))
    monkeypatch.setenv("DR_DOWNLOAD_FFMPEG", str(ffmpeg))

    command = build_command("yt-dlp.exe", "https://example.com", "audio-mp3", str(tmp_path), "none")

    assert command[command.index("--ffmpeg-location") + 1] == str(ffmpeg)


def test_parse_progress_returns_normalized_numbers():
    value = parse_progress("__DR_PROGRESS__42.5%|1024|4096|512|6")
    assert value == {
        "progress": 42,
        "bytes_downloaded": 1024,
        "total_bytes": 4096,
        "speed_bps": 512,
        "eta_seconds": 6,
    }
    assert parse_progress("ordinary yt-dlp output") is None


def test_inspection_uses_supported_javascript_runtime_with_browser_cookies(monkeypatch, tmp_path):
    node = tmp_path / "node.exe"
    node.write_bytes(b"node")
    monkeypatch.setenv("DR_DOWNLOAD_NODE", str(node))
    completed = type(
        "Completed",
        (),
        {"returncode": 0, "stdout": '{"title": "ok"}', "stderr": ""},
    )()

    with patch("backend.engine_runner.subprocess.run", return_value=completed) as run:
        assert inspect_with_engine("yt-dlp.exe", "https://example.com/video", "firefox") == {
            "title": "ok"
        }

    command = run.call_args.args[0]
    assert command[command.index("--js-runtimes") + 1] == f"node:{node}"
    assert command[command.index("--cookies-from-browser") + 1] == "firefox"


def test_node_runtime_fails_closed_when_bundled_executable_is_missing(monkeypatch):
    monkeypatch.delenv("DR_DOWNLOAD_NODE", raising=False)

    with pytest.raises(RuntimeError, match="Node runtime is unavailable"):
        node_runtime_argument()


def test_engine_resolution_fails_closed_when_yt_dlp_is_missing(monkeypatch, tmp_path):
    monkeypatch.delenv("DR_DOWNLOAD_YTDLP", raising=False)
    monkeypatch.setenv("DR_DOWNLOAD_DATA_DIR", str(tmp_path))

    with pytest.raises(RuntimeError, match="yt-dlp engine is unavailable"):
        resolve_engine()


def test_download_cancellation_kills_process_if_terminate_times_out(tmp_path, monkeypatch):
    node = tmp_path / "node.exe"
    node.write_bytes(b"node")
    monkeypatch.setenv("DR_DOWNLOAD_NODE", str(node))
    class HangingProcess:
        stdout = ["progress output\n"]
        returncode = None

        def terminate(self):
            self.terminated = True

        def kill(self):
            self.killed = True

        def wait(self, timeout=None):
            if not getattr(self, "killed", False):
                raise subprocess.TimeoutExpired("yt-dlp", timeout)
            return -9

    process = HangingProcess()
    cancelled = threading.Event()
    cancelled.set()
    with patch("backend.engine_runner.subprocess.Popen", return_value=process):
        try:
            download_with_engine(
                "yt-dlp.exe",
                "https://example.com/video",
                "audio-mp3",
                str(tmp_path),
                "none",
                lambda _progress: None,
                cancelled,
            )
        except RuntimeError as exc:
            assert str(exc) == "Download cancelled"
        else:  # pragma: no cover - defensive assertion
            raise AssertionError("cancellation must abort the download")
    assert process.terminated is True
    assert process.killed is True
