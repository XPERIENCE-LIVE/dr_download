"""Playback boundaries; isolated units plus real bundled-FFmpeg integration."""
import asyncio
import json
import math
import subprocess
import threading
from pathlib import Path
from uuid import uuid4

import pytest
import httpx
from fastapi.testclient import TestClient

from backend import config
from backend.playback_service import (
    PlaybackError, PlaybackManager, build_stream_command, select_streams,
    sponsor_segments, validate_provider_url, validate_start, _packet_time,
)


def sample_info():
    return {"id": "test", "title": "A title", "duration": 60.5, "formats": [
        {"url": "https://cdn.test/video", "height": 1080, "vcodec": "avc1.640028", "acodec": "none"},
        {"url": "https://cdn.test/audio", "vcodec": "none", "acodec": "mp4a.40.2", "abr": 128},
        {"url": "https://cdn.test/drm", "height": 2160, "vcodec": "av01", "acodec": "opus", "has_drm": True},
    ]}


@pytest.mark.parametrize("url", ["https://youtube.com/watch?v=test", "https://youtu.be/test", "https://player.vimeo.com/video/1"])
def test_provider_urls(url):
    assert validate_provider_url(url) == url


@pytest.mark.parametrize("url", ["http://youtube.com/watch?v=x", "https://youtube.com.evil.test/x", "file:///etc/passwd", "https://user:password@vimeo.com/1", "https://127.0.0.1/test", "https://youtube.com:8443/x"])
def test_provider_url_trust_boundary(url):
    with pytest.raises(PlaybackError):
        validate_provider_url(url)


def test_selects_supported_video_audio_without_drm():
    selection = select_streams(sample_info(), 1080)
    assert selection["video"]["url"].endswith("/video")
    assert selection["audio"]["url"].endswith("/audio")
    assert selection["height"] == 1080


def test_equal_bitrate_audio_respects_provider_language_and_quality():
    info = sample_info()
    first = info["formats"][1]
    first.update(abr=128, quality=2.5, language_preference=-1)
    info["formats"].append({**first, "url": "https://cdn.test/standard", "quality": 3})
    assert select_streams(info, 1080)["audio"]["url"].endswith("standard")


def test_demuxing_error_is_failure_even_when_ffmpeg_exits_zero():
    import sys
    manager = PlaybackManager()
    safe = manager.register(sample_info(), 1080)
    session = manager.sessions[safe["session_id"]]
    process = subprocess.Popen([sys.executable, "-c", "raise SystemExit(0)"], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    process.wait(timeout=5)
    process._dr_errors = bytearray(b"Error during demuxing: I/O error")
    session["process"] = process
    manager.release_stream(session, process)
    assert manager.describe(safe["session_id"])["status"] == "failed"


def test_muxed_vimeo_format_does_not_require_separate_audio():
    info = sample_info()
    info["formats"] = [{"url": "https://cdn.test/muxed", "height": 720, "vcodec": "h264", "acodec": "aac"}]
    selection = select_streams(info, 1080)
    assert selection["audio"] is None


@pytest.mark.parametrize("flag", ["is_live", "has_drm"])
def test_rejects_live_or_protected_media(flag):
    info = sample_info()
    info[flag] = True
    with pytest.raises(PlaybackError) as error:
        select_streams(info, 1080)
    assert error.value.code == ("live_unsupported" if flag == "is_live" else "drm_protected")


def test_rejects_unplayable_height_or_audio():
    with pytest.raises(PlaybackError, match="stream_unavailable"):
        select_streams(sample_info(), 720)
    info = sample_info()
    info["formats"][1]["acodec"] = "vorbis"
    with pytest.raises(PlaybackError, match="stream_unavailable"):
        select_streams(info, 1080)


@pytest.mark.parametrize("protected_track", [0, 1])
def test_partial_drm_flags_reject_required_protected_video_or_audio(protected_track):
    info = sample_info()
    info["formats"] = info["formats"][:2]
    info["formats"][protected_track]["has_drm"] = True
    with pytest.raises(PlaybackError, match="drm_protected"):
        select_streams(info, 1080)


def test_known_protected_unknown_codec_audio_is_never_probed(monkeypatch):
    manager = PlaybackManager()
    info = sample_info()
    info["formats"] = info["formats"][:2]
    info["formats"][1].update(acodec=None, has_drm=True)
    monkeypatch.setattr("backend.playback_service._binary", lambda name: Path(name))
    def forbidden(*args, **kwargs):
        pytest.fail("Known DRM audio reached ffprobe")
    monkeypatch.setattr(manager, "run_process", forbidden)
    with pytest.raises(PlaybackError, match="drm_protected"):
        manager.register(info, 1080)


def test_clear_unknown_audio_is_verified_even_when_another_audio_is_protected(monkeypatch):
    manager = PlaybackManager()
    info = sample_info()
    protected = {**info["formats"][1], "url": "https://cdn.test/protected", "has_drm": True}
    info["formats"][1]["acodec"] = None
    info["formats"].append(protected)
    monkeypatch.setattr("backend.playback_service._binary", lambda name: Path(name))
    monkeypatch.setattr(manager, "run_process", lambda *args, **kwargs: subprocess.CompletedProcess([], 0, b'{"streams":[{"codec_type":"audio","codec_name":"aac"}]}', b''))
    safe = manager.register(info, 1080)
    assert manager.sessions[safe["session_id"]]["selection"]["audio"]["url"] == "https://cdn.test/audio"
    manager.shutdown()


@pytest.mark.parametrize("start", [0, 15.23, 60.5])
def test_seek_accepts_finite_decimal_seconds(start):
    assert validate_start(start, 60.5) == start


@pytest.mark.parametrize("start", [-1, 61, math.nan, math.inf, True, "15.23"])
def test_seek_rejects_untrusted_values(start):
    with pytest.raises(PlaybackError):
        validate_start(start, 60.5)


def test_unknown_duration_only_allows_initial_start():
    assert validate_start(0, None) == 0
    with pytest.raises(PlaybackError):
        validate_start(1, None)


@pytest.mark.parametrize("packet,requested,expected", [(b"-1.23", 3.23, 2), (b"0", 0, 0), (b"-2e0", 4, 2)])
def test_owned_packet_timestamp_accounts_for_requested_seek(packet, requested, expected):
    assert _packet_time(b"[info] demuxer+ffmpeg -> type:video pkt_pts_time:" + packet, requested) == ("video", pytest.approx(expected))
    assert _packet_time(b"[info] demuxer+ffmpeg -> type:audio pkt_pts_time:0", requested) == ("audio", requested)


@pytest.mark.parametrize("packet", [b"nan", b"inf", b"N/A"])
def test_owned_packet_timestamp_rejects_nonfinite_or_invalid_time(packet):
    with pytest.raises(PlaybackError, match="stream_unavailable"):
        _packet_time(b"[info] demuxer+ffmpeg -> type:video pkt_pts_time:" + packet, 3)


def test_stop_interrupts_a_stream_waiting_for_its_first_packet(monkeypatch):
    import sys
    import time
    from concurrent.futures import ThreadPoolExecutor
    manager = PlaybackManager()
    safe = manager.register(sample_info(), 1080)
    session = manager.sessions[safe["session_id"]]
    monkeypatch.setattr("backend.playback_service._binary", lambda name: Path(name))
    monkeypatch.setattr("backend.playback_service.build_stream_command", lambda *args:
                        [sys.executable, "-c", "import time; time.sleep(90)"])
    with ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(manager.open_stream, safe["session_id"], 0)
        deadline = time.monotonic() + 5
        while session["process"] is None and time.monotonic() < deadline:
            time.sleep(0.01)
        process = session["process"]
        try:
            assert process is not None
            manager.stop(safe["session_id"])
            with pytest.raises(PlaybackError, match="playback_cancelled"):
                future.result(timeout=3)
            assert process.poll() is not None
        finally:
            manager.shutdown()


def test_ffmpeg_uses_both_headers_separately_and_no_shell(tmp_path):
    selection = select_streams(sample_info(), 1080)
    selection["video"]["http_headers"] = {"Referer": "https://youtube.com/"}
    selection["audio"]["http_headers"] = {"User-Agent": "Unit test"}
    command = build_stream_command(tmp_path / "ffmpeg.exe", selection, 15.23)
    assert command.count("-i") == 2
    assert command.count("-ss") == 2
    assert command[command.index("-c") + 1] == "copy"
    assert command[-1] == "pipe:1"
    assert "Referer: https://youtube.com/\r\n" in command
    assert "User-Agent: Unit test\r\n" in command


def test_sponsorblock_queries_hash_prefix_only_when_consented(monkeypatch, tmp_path):
    monkeypatch.setattr(config, "CONFIG_FILE", str(tmp_path / "config.json"))
    config.save_config({"sponsorblock_consent": False})
    info = {"id": "BaW_jenozKc", "extractor_key": "Youtube"}
    assert sponsor_segments(info) == ([], "off")


def test_session_metadata_never_exposes_upstream_urls_or_headers():
    manager = PlaybackManager()
    session = manager.register(sample_info(), 1080)
    safe = manager.describe(session["session_id"])
    encoded = json.dumps(safe)
    assert "cdn.test" not in encoded
    assert "http_headers" not in encoded
    assert safe["duration"] == 60.5
    manager.shutdown()


def test_session_expiry_is_explicit():
    manager = PlaybackManager()
    session = manager.register(sample_info(), 1080)
    manager.sessions[session["session_id"]]["expires_at"] = 0
    with pytest.raises(PlaybackError) as error:
        manager.describe(session["session_id"])
    assert error.value.code == "stream_expired"
    assert error.value.status == 410


@pytest.mark.parametrize("expiry", ["invalid", "nan", "inf"])
def test_invalid_provider_expiry_fails_closed(expiry):
    info = sample_info()
    info["formats"][0]["url"] += "?expire=" + expiry
    with pytest.raises(PlaybackError, match="stream_unavailable"):
        PlaybackManager().register(info, 1080)


@pytest.mark.parametrize("url", ["https://@youtube.com/x", "https://youtube.com/x\x7f", "https://youtube.com\\evil.test/x"])
def test_provider_url_rejects_ambiguous_authority(url):
    with pytest.raises(PlaybackError):
        validate_provider_url(url)


def test_stopped_session_cannot_spawn_a_late_stream(monkeypatch):
    manager = PlaybackManager()
    safe = manager.register(sample_info(), 1080)
    original = manager._session
    def stop_after_lookup(identifier):
        session = original(identifier)
        manager.stop(identifier)
        return session
    monkeypatch.setattr(manager, "_session", stop_after_lookup)
    with pytest.raises(PlaybackError, match="playback_cancelled"):
        manager.open_stream(safe["session_id"], 0)


def test_shutdown_terminates_owned_resolution_and_rejects_late_registration():
    import sys
    import time
    manager = PlaybackManager()
    errors = []
    def resolve():
        try:
            manager.run_process([sys.executable, "-c", "import time; time.sleep(90)"], timeout=95)
        except PlaybackError as error:
            errors.append(error.code)
    thread = threading.Thread(target=resolve, daemon=True)
    thread.start()
    deadline = time.monotonic() + 5
    while not getattr(manager, "pending", ()) and thread.is_alive() and time.monotonic() < deadline:
        time.sleep(0.01)
    owned = list(getattr(manager, "pending", ()))
    manager.shutdown()
    thread.join(timeout=5)
    assert owned and all(process.poll() is not None for process in owned)
    assert not thread.is_alive()
    assert errors == ["playback_cancelled"]
    with pytest.raises(PlaybackError, match="playback_cancelled"):
        manager.register(sample_info(), 1080)


def test_pending_process_limit_rejects_fifth_and_shutdown_cleans_all_children():
    import sys
    import time
    from concurrent.futures import ThreadPoolExecutor
    manager = PlaybackManager()
    command = [sys.executable, "-c", "import time; time.sleep(90)"]
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = [executor.submit(manager.run_process, command, timeout=95) for _ in range(4)]
        try:
            deadline = time.monotonic() + 5
            while len(manager.pending) < 4 and time.monotonic() < deadline:
                time.sleep(0.01)
            owned = list(manager.pending)
            assert len(owned) == 4
            with pytest.raises(PlaybackError, match="playback_busy") as error:
                manager.run_process([sys.executable, "-c", "print('should not spawn')"], timeout=5)
            assert error.value.status == 429 and len(manager.pending) == 4
        finally:
            manager.shutdown()
        for future in futures:
            with pytest.raises(PlaybackError, match="playback_cancelled"):
                future.result(timeout=5)
    assert all(process.poll() is not None for process in owned)
    assert manager.pending == set()


def test_hls_audio_with_unknown_codec_is_verified_before_selection(monkeypatch):
    manager = PlaybackManager()
    info = sample_info()
    info["formats"][1].update(acodec=None, protocol="m3u8_native")
    monkeypatch.setattr("backend.playback_service._binary", lambda name: Path(name))
    calls = []
    def probe(command, **kwargs):
        calls.append(command)
        return subprocess.CompletedProcess(command, 0, b'{"streams":[{"codec_type":"audio","codec_name":"aac"}]}', b'')
    monkeypatch.setattr(manager, "run_process", probe)
    safe = manager.register(info, 1080)
    assert safe["height"] == 1080 and len(calls) == 1
    assert manager.sessions[safe["session_id"]]["selection"]["audio"]["acodec"] == "aac"


def test_progressive_unknown_codecs_are_verified_and_preferred_at_same_height(monkeypatch):
    manager = PlaybackManager()
    info = sample_info()
    info["formats"].append({"url": "https://cdn.test/public.mp4", "height": 1080,
                            "protocol": "https", "ext": "mp4", "vcodec": None, "acodec": None})
    monkeypatch.setattr("backend.playback_service._binary", lambda name: Path(name))
    calls = []
    def probe(command, **kwargs):
        calls.append(command)
        return subprocess.CompletedProcess(command, 0,
            b'{"streams":[{"codec_type":"audio","codec_name":"aac"},{"codec_type":"video","codec_name":"h264"}]}', b'')
    monkeypatch.setattr(manager, "run_process", probe)
    safe = manager.register(info, 1080)
    selection = manager.sessions[safe["session_id"]]["selection"]
    assert selection["audio"] is None and selection["video"]["url"].endswith("public.mp4")
    assert len(calls) == 1


def test_hls_drm_key_is_rejected_with_explicit_cause(monkeypatch):
    manager = PlaybackManager()
    info = sample_info()
    info["formats"][1].update(acodec=None, protocol="m3u8_native")
    monkeypatch.setattr("backend.playback_service._binary", lambda name: Path(name))
    monkeypatch.setattr(manager, "run_process", lambda command, **kwargs:
                        subprocess.CompletedProcess(command, 1, b'{}', b'Unable to open key file skd://drm'))
    with pytest.raises(PlaybackError, match="drm_protected"):
        manager.register(info, 1080)


def test_sponsorblock_prefix_request_and_segment_bounds(monkeypatch):
    import hashlib
    calls = []
    monkeypatch.setattr("backend.playback_service.load_config", lambda: {"sponsorblock_consent": True})
    class Client:
        def __init__(self, **kwargs):
            assert kwargs == {"timeout": 5, "trust_env": False}
        def __enter__(self):
            return self
        def __exit__(self, *args):
            return False
        def get(self, url, **kwargs):
            calls.append((url, kwargs))
            return httpx.Response(200, request=httpx.Request("GET", url), json=[
                {"videoID": "other", "segments": [{"category": "sponsor", "segment": [0, 2]}]},
                {"videoID": "BaW_jenozKc", "segments": [{"category": "sponsor", "segment": [1.25, 4.5]},
                                                      {"category": "sponsor", "segment": [4, 99]},
                                                      {"category": "intro", "segment": [0, 1]}]},
            ])
    monkeypatch.setattr("backend.playback_service.httpx.Client", Client)
    segments, status = sponsor_segments({"id": "BaW_jenozKc", "extractor_key": "Youtube", "duration": 10})
    assert segments == [{"start": 1.25, "end": 4.5}] and status == "available"
    assert calls[0][0].endswith(hashlib.sha256(b"BaW_jenozKc").hexdigest()[:4])
    assert "BaW_jenozKc" not in json.dumps(calls)


def test_playback_api_rejects_unconsented_browser_before_engine(monkeypatch, tmp_path):
    monkeypatch.setattr(config, "CONFIG_FILE", str(tmp_path / "config.json"))
    config.save_config({"cookie_consent": False, "cookie_source": "edge"})
    from backend.main import app
    client = TestClient(app)
    response = client.post("/playback", json={"url": "https://youtu.be/test", "cookie_source": "edge"})
    assert response.status_code == 403
    assert response.json()["detail"]["code"] == "browser_consent_required"
    client.close()


def test_new_stream_cleanup_cannot_kill_a_replacement():
    manager = PlaybackManager()
    first = object()
    newer = object()
    session = {"process": newer, "lock": threading.RLock(), "status": "playing"}
    manager.release_stream(session, first)
    assert session["process"] is newer


def test_late_seek_cannot_replace_the_latest_request(monkeypatch):
    manager = PlaybackManager()
    safe = manager.register(sample_info(), 1080)
    first = manager.reserve_stream(safe["session_id"])
    manager.reserve_stream(safe["session_id"])
    with pytest.raises(PlaybackError) as error:
        manager.open_stream(safe["session_id"], 0, first)
    assert error.value.code == "playback_cancelled"


def test_late_browser_retry_cannot_reserve_an_older_source_or_kill_current_process():
    import sys
    manager = PlaybackManager()
    safe = manager.register(sample_info(), 1080)
    identifier = safe["session_id"]
    process = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(90)"], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    try:
        manager.reserve_stream(identifier, revision=2)
        session = manager.sessions[identifier]
        session["process"] = process
        with pytest.raises(PlaybackError, match="playback_cancelled"):
            manager.reserve_stream(identifier, revision=1)
        assert process.poll() is None and session["process"] is process
    finally:
        manager.stop(identifier)
        if process.poll() is None:
            process.kill(); process.wait(timeout=5)


@pytest.mark.parametrize("revision", [-1, True, "1", math.inf, 2147483648])
def test_stream_revision_is_a_bounded_nonnegative_integer(revision):
    manager = PlaybackManager()
    safe = manager.register(sample_info(), 1080)
    try:
        with pytest.raises(PlaybackError) as error:
            manager.reserve_stream(safe["session_id"], revision)
        assert error.value.status == 422
    finally:
        manager.shutdown()


def test_stream_process_error_is_visible_without_leaking_provider_data():
    manager = PlaybackManager()
    safe = manager.register(sample_info(), 1080)
    session = manager.sessions[safe["session_id"]]
    process = subprocess.Popen([__import__('sys').executable, "-c", "raise SystemExit(3)"], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    process.wait(timeout=10)
    session["process"] = process
    manager.release_stream(session, process)
    metadata = manager.describe(safe["session_id"])
    assert metadata["status"] == "failed"
    assert metadata["error"]["code"] == "stream_unavailable"


def test_stdout_eof_waits_for_process_failure_instead_of_reporting_success():
    import sys
    manager = PlaybackManager()
    safe = manager.register(sample_info(), 1080)
    session = manager.sessions[safe["session_id"]]
    process = subprocess.Popen([sys.executable, "-c", "import os,time; os.close(1); time.sleep(0.2); raise SystemExit(7)"],
                               stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    session["process"] = process
    async def consume():
        return [chunk async for chunk in manager.stream(session, process)]
    assert asyncio.run(consume()) == []
    assert manager.describe(safe["session_id"])["status"] == "failed"


def test_bundled_ffmpeg_stream_is_decodable_and_owned_process_stops(tmp_path):
    ffmpeg = Path(__file__).resolve().parents[2] / "electron/resources/ffmpeg/ffmpeg.exe"
    ffprobe = ffmpeg.with_name("ffprobe.exe")
    if not ffmpeg.is_file() or not ffprobe.is_file():
        pytest.skip("Bundled FFmpeg runtime not prepared in this checkout")
    source = tmp_path / "source.mp4"
    subprocess.run([str(ffmpeg), "-v", "error", "-f", "lavfi", "-i", "testsrc2=size=320x180:rate=25", "-f", "lavfi", "-i", "sine=frequency=440", "-t", "6", "-c:v", "libx264", "-g", "50", "-c:a", "aac", str(source)], check=True, timeout=30)
    selection = {"video": {"url": str(source)}, "audio": None, "height": 180}
    command = build_stream_command(ffmpeg, selection, 0)
    result = subprocess.run(command, capture_output=True, check=True, timeout=30)
    probe = subprocess.run([str(ffprobe), "-v", "error", "-show_entries", "stream=codec_type", "-of", "json", "pipe:0"], input=result.stdout, capture_output=True, check=True, timeout=30)
    assert {stream["codec_type"] for stream in json.loads(probe.stdout)["streams"]} == {"video", "audio"}
    manager = PlaybackManager()
    safe = manager.register(sample_info(), 1080)
    session = manager.sessions[safe["session_id"]]
    process = subprocess.Popen([str(ffmpeg), "-v", "error", "-re", "-i", str(source), "-f", "null", "-"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    session["process"] = process
    manager.stop(safe["session_id"])
    assert process.poll() is not None


def test_bundled_stream_flushes_fragments_before_a_long_gop_finishes(tmp_path):
    ffmpeg = Path(__file__).resolve().parents[2] / "electron/resources/ffmpeg/ffmpeg.exe"
    if not ffmpeg.is_file():
        pytest.skip("Bundled FFmpeg runtime not prepared in this checkout")
    source = tmp_path / "long-gop.mp4"
    subprocess.run([str(ffmpeg), "-v", "error", "-f", "lavfi", "-i", "testsrc2=size=160x90:rate=25",
                    "-f", "lavfi", "-i", "sine=frequency=440", "-t", "8", "-c:v", "libx264", "-g", "250",
                    "-c:a", "aac", str(source)], check=True, timeout=30)
    command = build_stream_command(ffmpeg, {"video": {"url": str(source)}, "audio": None}, 0)
    command[command.index("-i"):command.index("-i")] = ["-re"]
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    manager = PlaybackManager()
    safe = manager.register(sample_info(), 1080)
    manager.sessions[safe["session_id"]]["process"] = process
    fragment = threading.Event()
    def read():
        data = bytearray()
        while chunk := process.stdout.read1(65536):
            data.extend(chunk)
            if b"moof" in data:
                fragment.set()
                return
    reader = threading.Thread(target=read, daemon=True)
    reader.start()
    try:
        assert fragment.wait(timeout=3), "No MP4 media fragment before the long GOP completed"
        assert process.poll() is None
    finally:
        manager.stop(safe["session_id"])
        reader.join(timeout=3)


def test_bundled_seek_uses_owned_ffmpeg_timestamps_without_a_second_probe(tmp_path, monkeypatch):
    ffmpeg = Path(__file__).resolve().parents[2] / "electron/resources/ffmpeg/ffmpeg.exe"
    if not ffmpeg.is_file():
        pytest.skip("Bundled FFmpeg runtime not prepared in this checkout")
    source = tmp_path / "seek.mp4"
    subprocess.run([str(ffmpeg), "-v", "error", "-f", "lavfi", "-i", "testsrc2=size=160x90:rate=25",
                    "-f", "lavfi", "-i", "sine=frequency=440", "-t", "6", "-c:v", "libx264", "-g", "50",
                    "-c:a", "aac", str(source)], check=True, timeout=30)
    manager = PlaybackManager()
    safe = manager.register(sample_info(), 1080)
    session = manager.sessions[safe["session_id"]]
    session["selection"] = {"video": {"url": str(source)}, "audio": None, "height": 90}
    monkeypatch.setenv("DR_DOWNLOAD_FFMPEG", str(ffmpeg.parent))
    def forbidden(*args, **kwargs):
        pytest.fail("Seek spawned a duplicate network probe")
    monkeypatch.setattr(manager, "run_process", forbidden)
    try:
        _, process = manager.open_stream(safe["session_id"], 3.23, manager.reserve_stream(safe["session_id"]))
        assert session["actual_start"] == pytest.approx(2, abs=0.01)
        async def consume():
            return b"".join([chunk async for chunk in manager.stream(session, process)])
        data = asyncio.run(consume())
        probe = subprocess.run([str(ffmpeg.with_name("ffprobe.exe")), "-v", "error", "-show_entries",
                                "stream=codec_type", "-of", "json", "pipe:0"],
                               input=data, capture_output=True, check=True, timeout=30)
        assert {track["codec_type"] for track in json.loads(probe.stdout)["streams"]} == {"video", "audio"}
        assert session["status"] == "ended" and process.poll() is not None
    finally:
        manager.shutdown()


@pytest.mark.parametrize("recover", [True, False])
def test_bundled_http_stream_recovers_or_fails_visibly_after_transport_disconnect(tmp_path, monkeypatch, recover):
    from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
    import socket
    import time
    ffmpeg = Path(__file__).resolve().parents[2] / "electron/resources/ffmpeg/ffmpeg.exe"
    if not ffmpeg.is_file():
        pytest.skip("Bundled FFmpeg runtime not prepared in this checkout")
    source = tmp_path / "network.mp4"
    subprocess.run([str(ffmpeg), "-v", "error", "-f", "lavfi", "-i", "testsrc2=size=320x180:rate=25",
                    "-f", "lavfi", "-i", "sine=frequency=440", "-t", "6", "-c:v", "libx264", "-g", "50",
                    "-c:a", "aac", "-movflags", "+faststart", str(source)], check=True, timeout=30)
    data = source.read_bytes()
    interrupted = threading.Event()
    requests = []
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            return
        def do_GET(self):
            offset = int(self.headers.get("Range", "bytes=0-").split("=")[1].split("-")[0])
            requests.append(offset)
            if interrupted.is_set() and not recover:
                self.send_error(503)
                return
            self.send_response(206 if offset else 200)
            self.send_header("Content-Type", "video/mp4")
            self.send_header("Accept-Ranges", "bytes")
            self.send_header("Content-Length", str(len(data) - offset))
            if offset:
                self.send_header("Content-Range", f"bytes {offset}-{len(data)-1}/{len(data)}")
            self.end_headers()
            if not interrupted.is_set():
                interrupted.set()
                self.wfile.write(data[offset:offset + 65536]); self.wfile.flush()
                self.connection.shutdown(socket.SHUT_RDWR)
                self.close_connection = True
            else:
                self.wfile.write(data[offset:])
    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    serving = threading.Thread(target=server.serve_forever, daemon=True)
    serving.start()
    manager = PlaybackManager()
    safe = manager.register(sample_info(), 1080)
    session = manager.sessions[safe["session_id"]]
    session["duration"] = 6
    session["selection"] = {"video": {"url": f"http://127.0.0.1:{server.server_port}/video.mp4"}, "audio": None, "height": 180}
    monkeypatch.setenv("DR_DOWNLOAD_FFMPEG", str(ffmpeg.parent))
    begun = time.monotonic()
    try:
        _, process = manager.open_stream(safe["session_id"], 0, manager.reserve_stream(safe["session_id"]))
        async def consume():
            return b"".join([chunk async for chunk in manager.stream(session, process)])
        output = asyncio.run(consume())
        probe = subprocess.run([str(ffmpeg.with_name("ffprobe.exe")), "-v", "error", "-count_frames", "-select_streams", "v:0",
                                "-show_entries", "stream=nb_read_frames", "-of", "json", "pipe:0"],
                               input=output, capture_output=True, check=True, timeout=30)
        frames = int(json.loads(probe.stdout)["streams"][0]["nb_read_frames"])
        assert interrupted.is_set() and len(requests) >= 2 and any(offset > 0 for offset in requests)
        assert time.monotonic() - begun < 10 and len(requests) <= 4
        if recover:
            assert frames == 150
            assert session["status"] == "ended", (process.returncode, bytes(process._dr_errors), process._dr_last_times)
        else:
            assert 0 < frames < 150 and session["status"] == "failed"
    finally:
        manager.shutdown(); server.shutdown(); server.server_close(); serving.join(timeout=3)
