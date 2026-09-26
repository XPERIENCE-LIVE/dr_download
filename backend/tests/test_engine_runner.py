import subprocess
import threading
from pathlib import Path
from unittest.mock import patch

import pytest

from backend.engine_runner import (
    FILE_PREFIX,
    _terminate_process_tree,
    build_command,
    download_with_cookie_fallback,
    download_with_engine,
    inspect_with_engine,
    node_runtime_argument,
    parse_progress,
    resolve_engine,
    unique_destination,
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


def test_build_command_rejects_blank_format(monkeypatch, tmp_path):
    node = tmp_path / "node.exe"
    node.write_bytes(b"node")
    monkeypatch.setenv("DR_DOWNLOAD_NODE", str(node))

    with pytest.raises(ValueError, match="Unsupported format"):
        build_command("yt-dlp.exe", "https://example.com", "   ", str(tmp_path), "none")


def test_build_command_merges_audio_for_specific_streams(monkeypatch, tmp_path):
    node = tmp_path / "node.exe"
    node.write_bytes(b"node")
    monkeypatch.setenv("DR_DOWNLOAD_NODE", str(node))

    # Numeric video-only stream (e.g. YouTube 1080p) must gain an audio track.
    numeric = build_command("yt-dlp.exe", "https://example.com", "137", str(tmp_path), "none")
    assert numeric[numeric.index("--format") + 1] == "137+bestaudio/137"

    # Non-numeric stream ids from other extractors must be accepted, not rejected.
    string_id = build_command("yt-dlp.exe", "https://vimeo.com/1", "hls-2500", str(tmp_path), "none")
    assert string_id[string_id.index("--format") + 1] == "hls-2500+bestaudio/hls-2500"


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


def test_unique_destination_never_overwrites_existing_files(tmp_path):
    # First download of a title lands on the plain name.
    assert unique_destination(tmp_path, "song.mp3") == tmp_path / "song.mp3"

    # With the file already present (e.g. user's library), a new download gets
    # a numbered name instead of clobbering it.
    (tmp_path / "song.mp3").write_bytes(b"existing")
    assert unique_destination(tmp_path, "song.mp3") == tmp_path / "song (1).mp3"

    (tmp_path / "song (1).mp3").write_bytes(b"existing")
    assert unique_destination(tmp_path, "song.mp3") == tmp_path / "song (2).mp3"


def test_download_stages_then_moves_without_overwriting(tmp_path, monkeypatch):
    node = tmp_path / "node.exe"
    node.write_bytes(b"node")
    monkeypatch.setenv("DR_DOWNLOAD_NODE", str(node))
    dest = tmp_path / "out"
    dest.mkdir()
    (dest / "clip.mp3").write_bytes(b"user library file")  # pre-existing collision

    class FakeProcess:
        returncode = 0

        def __init__(self, staging_line):
            self.stdout = [staging_line + "\n"]

        def wait(self):
            return 0

    def fake_popen(command, **kwargs):
        # yt-dlp writes into the staging dir (the --output path we passed it).
        staging = Path(command[command.index("--output") + 1]).parent
        produced = staging / "clip.mp3"
        produced.write_bytes(b"freshly downloaded")
        return FakeProcess(f"{FILE_PREFIX}{produced}")

    with patch("backend.engine_runner.subprocess.Popen", side_effect=fake_popen):
        result = download_with_engine(
            "yt-dlp.exe", "https://x/v", "audio-mp3", str(dest), "none", lambda _d: None, threading.Event()
        )

    assert result == str(dest / "clip (1).mp3")  # new file, numbered
    assert (dest / "clip.mp3").read_bytes() == b"user library file"  # original untouched
    assert (dest / "clip (1).mp3").read_bytes() == b"freshly downloaded"
    assert not any(p.name.startswith(".dr-download-") for p in dest.iterdir())  # staging cleaned


def test_cookie_fallback_retries_without_cookies_when_browser_locks_store():
    cancelled = threading.Event()
    calls = []

    def fake_download(executable, url, format_id, output_dir, cookie_source, on_progress, cancel):
        calls.append(cookie_source)
        if cookie_source != "none":
            raise RuntimeError("Permission denied while reading the cookie database")
        return "video.mp3"

    with patch("backend.engine_runner.download_with_engine", side_effect=fake_download):
        result = download_with_cookie_fallback(
            "yt-dlp.exe", "https://x/v", "audio-mp3", "/out", "edge", lambda _d: None, cancelled
        )

    assert result == "video.mp3"
    assert calls == ["edge", "none"]  # tried cookies first, then fell back


def test_cookie_fallback_does_not_mask_real_download_errors():
    cancelled = threading.Event()
    calls = []

    def fake_download(executable, url, format_id, output_dir, cookie_source, on_progress, cancel):
        calls.append(cookie_source)
        raise RuntimeError("HTTP Error 404: Not Found")

    with patch("backend.engine_runner.download_with_engine", side_effect=fake_download):
        with pytest.raises(RuntimeError, match="404"):
            download_with_cookie_fallback(
                "yt-dlp.exe", "https://x/v", "audio-mp3", "/out", "edge", lambda _d: None, cancelled
            )

    assert calls == ["edge"]  # non-cookie failure must not trigger a retry


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
