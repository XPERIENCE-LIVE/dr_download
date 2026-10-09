import subprocess
import threading
from pathlib import Path
from unittest.mock import patch

import pytest
from backend import config

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
    standard_filename,
    unique_destination,
)


@pytest.fixture(autouse=True)
def isolated_cookie_authorization(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "CONFIG_FILE", str(tmp_path / "config.json"))
    config.save_config({"cookie_source": "edge", "cookie_consent": False})


def test_windows_cancellation_terminates_the_process_tree():
    process = type("Process", (), {"pid": 4321, "wait": lambda self, timeout=None: 0})()

    with patch("backend.engine_runner.os.name", "nt"), patch(
        "backend.engine_runner.subprocess.run"
    ) as run:
        _terminate_process_tree(process)

    assert run.call_args.args[0] == ["taskkill", "/PID", "4321", "/T", "/F"]
    assert run.call_args.kwargs["shell"] is False


def test_build_command_uses_browser_only_when_consented(tmp_path, monkeypatch):
    config.save_config({"cookie_source": "edge", "cookie_consent": True})
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


def test_build_command_keeps_progress_despite_print_implying_quiet(monkeypatch, tmp_path):
    # --print implies --quiet, which silences progress: the UI bar would stay at 0%.
    node = tmp_path / "node.exe"
    node.write_bytes(b"node")
    monkeypatch.setenv("DR_DOWNLOAD_NODE", str(node))

    command = build_command("yt-dlp.exe", "https://example.com", "video-best", str(tmp_path), "none")

    assert "--print" in command
    assert "--progress" in command


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
    # Long titles (post descriptions) must not exceed NTFS' 255-char name limit.
    assert numeric[numeric.index("--trim-filenames") + 1] == "150"
    assert numeric[numeric.index("--format") + 1] == "137+ba[ext=m4a]/137+bestaudio/137"

    # Non-numeric stream ids from other extractors must be accepted, not rejected.
    string_id = build_command("yt-dlp.exe", "https://vimeo.com/1", "hls-2500", str(tmp_path), "none")
    assert string_id[string_id.index("--format") + 1] == "hls-2500+ba[ext=m4a]/hls-2500+bestaudio/hls-2500"


def test_best_video_prefers_aac_audio_that_windows_players_can_decode(monkeypatch, tmp_path):
    # YouTube's "best" audio is Opus; inside an MP4 most Windows players, TVs and
    # editors play it silently. AAC (m4a) first, any audio only as a fallback.
    node = tmp_path / "node.exe"
    node.write_bytes(b"node")
    monkeypatch.setenv("DR_DOWNLOAD_NODE", str(node))

    command = build_command("yt-dlp.exe", "https://example.com", "video-best", str(tmp_path), "none")

    assert command[command.index("--format") + 1] == "bv*+ba[ext=m4a]/bv*+ba/b"


def test_compatible_video_filters_codecs_and_remuxes_mp4(monkeypatch, tmp_path):
    node = tmp_path / "node.exe"
    node.write_bytes(b"node")
    monkeypatch.setenv("DR_DOWNLOAD_NODE", str(node))
    command = build_command("yt-dlp.exe", "https://example.com", "video-compatible", str(tmp_path), "none")
    assert command[command.index("--format") + 1] == (
        "bv[vcodec~='^(avc1|avc3|h264)']+ba[ext=m4a][acodec~='^(mp4a|aac)']/"
        "b[vcodec~='^(avc1|avc3|h264)'][acodec~='^(mp4a|aac)']"
    )
    assert command[command.index("--merge-output-format") + 1] == "mp4"
    assert command[command.index("--remux-video") + 1] == "mp4"


@pytest.mark.parametrize("format_id", ["137/best", "137+140", "best[ext=mp4]", "137,140", "(137)", " hls-2500", "x" * 129])
def test_build_command_rejects_selector_expressions_as_direct_ids(monkeypatch, tmp_path, format_id):
    node = tmp_path / "node.exe"
    node.write_bytes(b"node")
    monkeypatch.setenv("DR_DOWNLOAD_NODE", str(node))
    with pytest.raises(ValueError, match="Unsupported format"):
        build_command("yt-dlp.exe", "https://example.com", format_id, str(tmp_path), "none")


def test_build_command_uses_bundled_ffmpeg(monkeypatch, tmp_path):
    node = tmp_path / "node.exe"
    node.write_bytes(b"node")
    ffmpeg = tmp_path / "ffmpeg"
    ffmpeg.mkdir()
    (ffmpeg / "ffmpeg.exe").write_bytes(b"ffmpeg")
    monkeypatch.setenv("DR_DOWNLOAD_NODE", str(node))
    monkeypatch.setenv("DR_DOWNLOAD_FFMPEG", str(ffmpeg))

    command = build_command("yt-dlp.exe", "https://example.com", "audio-mp3", str(tmp_path), "none")

    assert command[command.index("--ffmpeg-location") + 1] == str(ffmpeg)


def test_build_command_fails_instead_of_producing_mute_video(monkeypatch, tmp_path):
    # yt-dlp "continues without ffmpeg" on a missing location: video and audio
    # are never merged and the user gets a video with no sound.
    node = tmp_path / "node.exe"
    node.write_bytes(b"node")
    monkeypatch.setenv("DR_DOWNLOAD_NODE", str(node))
    monkeypatch.setenv("DR_DOWNLOAD_FFMPEG", str(tmp_path / "missing-ffmpeg"))

    with pytest.raises(RuntimeError, match="FFmpeg is unavailable"):
        build_command("yt-dlp.exe", "https://example.com", "video-best", str(tmp_path), "none")


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
    config.save_config({"cookie_source": "firefox", "cookie_consent": True})
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


@pytest.mark.parametrize("consent, source", [(False, "edge"), (True, "firefox"), ("true", "edge"), (1, "edge")])
def test_engine_commands_cannot_read_a_revoked_browser_session(monkeypatch, tmp_path, consent, source):
    config.save_config({"cookie_consent": consent, "cookie_source": source})
    node = tmp_path / "node.exe"
    node.write_bytes(b"node")
    monkeypatch.setenv("DR_DOWNLOAD_NODE", str(node))
    command = build_command("yt-dlp.exe", "https://example.com", "audio-mp3", str(tmp_path), "edge")
    assert "--cookies-from-browser" not in command
    completed = type("Completed", (), {"returncode": 0, "stdout": '{"title": "public"}', "stderr": ""})()
    with patch("backend.engine_runner.subprocess.run", return_value=completed) as run:
        assert inspect_with_engine("yt-dlp.exe", "https://example.com", "edge")["title"] == "public"
    assert "--cookies-from-browser" not in run.call_args.args[0]


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


def test_standard_filename_replaces_yt_dlp_lookalike_chars():
    # yt-dlp swaps Windows-forbidden chars for full-width lookalikes.
    assert standard_filename("Live (15⧸16 - 20⧸21.05.2022).mp4") == "Live (15-16 - 20-21.05.2022).mp4"
    assert standard_filename("Artist： Song ｜ Live.mp3") == "Artist - Song - Live.mp3"
    assert standard_filename("Why？ ＂Hi＂ ＜a＞ b＊.webm") == "Why 'Hi' (a) b.webm"
    assert standard_filename("AC⧹DC 12：30.mp3") == "AC-DC 12-30.mp3"
    # Accents and non-Latin scripts are valid on Windows and stay untouched.
    assert standard_filename("Canción 東京.mp3") == "Canción 東京.mp3"
    # Nothing left but forbidden chars → still a usable name.
    assert standard_filename("？？？.mp4") == "download.mp4"


def test_download_survives_filename_mangled_by_console_encoding(tmp_path, monkeypatch):
    node = tmp_path / "node.exe"
    node.write_bytes(b"node")
    monkeypatch.setenv("DR_DOWNLOAD_NODE", str(node))
    dest = tmp_path / "out"
    dest.mkdir()

    class FakeProcess:
        def __init__(self, line):
            self.stdout = [line + "\n"]

        def wait(self):
            return 0

    def fake_popen(command, **kwargs):
        # yt-dlp saves "15/16" as "15⧸16" but its cp1252 stdout drops the
        # unencodable char, so the printed path does not exist on disk.
        staging = Path(command[command.index("--output") + 1]).parent
        (staging / "Live (15⧸16).webm").write_bytes(b"media")
        return FakeProcess(f"{FILE_PREFIX}{staging / 'Live (1516).webm'}")

    with patch("backend.engine_runner.subprocess.Popen", side_effect=fake_popen):
        result = download_with_engine(
            "yt-dlp.exe", "https://x/v", "audio-original", str(dest), "none", lambda _d: None, threading.Event()
        )

    assert result == str(dest / "Live (15-16).webm")
    assert (dest / "Live (15-16).webm").read_bytes() == b"media"


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


def test_download_retries_transient_youtube_403_then_gives_up():
    calls = []

    def flaky(*args):
        calls.append(1)
        if len(calls) == 1:
            raise RuntimeError("ERROR: unable to download video data: HTTP Error 403: Forbidden")
        return "video.mp4"

    with patch("backend.engine_runner.download_with_engine", side_effect=flaky):
        assert download_with_cookie_fallback(
            "yt-dlp.exe", "https://x/v", "video-best", "/out", "none", lambda _d: None, threading.Event()
        ) == "video.mp4"
    assert len(calls) == 2

    always = RuntimeError("HTTP Error 403: Forbidden")
    with patch("backend.engine_runner.download_with_engine", side_effect=always) as engine:
        with pytest.raises(RuntimeError, match="403"):
            download_with_cookie_fallback(
                "yt-dlp.exe", "https://x/v", "video-best", "/out", "none", lambda _d: None, threading.Event()
            )
    assert engine.call_count == 3  # bounded, never loops forever


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
