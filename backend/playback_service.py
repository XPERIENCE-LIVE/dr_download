"""Owned, memory-only playback sessions using the bundled extraction/media tools."""
import asyncio
import hashlib
import json
import math
import os
from pathlib import Path
import re
import subprocess
import threading
import time
from urllib.parse import parse_qs, urlsplit
from uuid import uuid4

import httpx
import anyio

from .config import authorized_cookie_source, load_config
from .engine_runner import (
    _terminate_process_tree, inspect_with_engine, resolve_engine,
)
from .error_mapping import classify_error

_TRANSPORT_ERRORS = ("[tls", "partial file", "error during demuxing", "stream ends prematurely")


class PlaybackError(RuntimeError):
    def __init__(self, code, status=400, detail=None):
        super().__init__(code)
        self.code = code
        self.status = status
        self.detail = detail or {"code": code, "message": code, "recovery": "Reload the video or check the source."}


def validate_provider_url(value):
    try:
        parsed = urlsplit(value)
        host = parsed.hostname or ""
        if (not isinstance(value, str) or not 8 <= len(value) <= 2048
                or parsed.scheme != "https" or parsed.username is not None or parsed.password is not None
                or parsed.port not in (None, 443) or parsed.fragment
                or any(character.isspace() or ord(character) < 32 or ord(character) == 127 or character == "\\" for character in value)
                or not any(host == domain or host.endswith("." + domain)
                           for domain in ("youtube.com", "youtu.be", "vimeo.com"))):
            raise ValueError
    except (ValueError, TypeError):
        raise PlaybackError("source_unsupported", 422) from None
    return value


def validate_start(value, duration):
    if (type(value) not in (int, float) or not math.isfinite(value) or value < 0
            or (duration is None and value != 0)
            or (duration is not None and value > duration)):
        raise PlaybackError("invalid_start", 422)
    return value


def _number(value):
    return value if type(value) in (int, float) and math.isfinite(value) and value >= 0 else None


def select_streams(info, max_height):
    if info.get("is_live") or info.get("live_status") in ("is_live", "is_upcoming", "post_live"):
        raise PlaybackError("live_unsupported")
    if info.get("has_drm"):
        raise PlaybackError("drm_protected")
    formats = info.get("formats") or [info]
    playable = [item for item in formats if item.get("url")]
    supported_videos = [item for item in playable
              if re.match(r"^(avc[13]|h264|vp0?9|av01|av1)", item.get("vcodec") or "")
              and 0 < (_number(item.get("height")) or 0) <= max_height
              and (item.get("acodec") in (None, "none") or
                   re.match(r"^(mp4a|aac|opus)", item.get("acodec") or ""))]
    videos = [item for item in supported_videos if not item.get("has_drm")]
    audios = [item for item in playable if not item.get("has_drm") and item.get("vcodec") == "none"
              and re.match(r"^(mp4a|aac|opus)", item.get("acodec") or "")]
    if not videos:
        code = "drm_protected" if supported_videos else "stream_unavailable"
        raise PlaybackError(code)
    # Select the best supported pair, including already-muxed Vimeo sources.
    videos.sort(key=lambda item: (item.get("height", 0),
                                  bool(re.match(r"^(avc|h264)", item.get("vcodec", ""))),
                                  item.get("acodec") not in (None, "none"),
                                  _number(item.get("tbr")) or 0), reverse=True)
    for video in videos:
        if video.get("acodec") not in (None, "none"):
            return {"video": video, "audio": None, "height": video["height"]}
        if audios:
            audio = max(audios, key=lambda item: (bool(re.match(r"^(mp4a|aac)", item.get("acodec", ""))),
                                                  _number(item.get("language_preference")) or 0,
                                                  _number(item.get("quality")) or 0,
                                                  _number(item.get("abr")) or 0))
            return {"video": video, "audio": audio, "height": video["height"]}
    protected_audio = any(item.get("has_drm") and item.get("vcodec") == "none"
                          and (item.get("acodec") is None or re.match(r"^(mp4a|aac|opus)", item.get("acodec") or ""))
                          for item in playable)
    raise PlaybackError("drm_protected" if protected_audio else "stream_unavailable")


def sponsor_segments(info):
    if load_config().get("sponsorblock_consent") is not True:
        return [], "off"
    if str(info.get("extractor_key") or info.get("extractor") or "").lower() not in ("youtube",):
        return [], "no_segments"
    identifier = str(info.get("id") or "")
    if not re.fullmatch(r"[A-Za-z0-9_-]{11}", identifier):
        return [], "no_segments"
    prefix = hashlib.sha256(identifier.encode()).hexdigest()[:4]
    try:
        # Consent is checked immediately before the external request, never inferred from UI.
        if load_config().get("sponsorblock_consent") is not True:
            return [], "off"
        with httpx.Client(timeout=5, trust_env=False) as client:
            response = client.get(f"https://sponsor.ajay.app/api/skipSegments/{prefix}",
                                  params={"categories": json.dumps(["sponsor", "selfpromo", "interaction"]),
                                          "actionTypes": '["skip"]'})
        if response.status_code == 404:
            return [], "no_segments"
        response.raise_for_status()
        entries = response.json()
        segments = []
        for entry in entries:
            if entry.get("videoID") != identifier:
                continue
            for segment in entry.get("segments", []):
                bounds = segment.get("segment")
                if (segment.get("category") not in {"sponsor", "selfpromo", "interaction"}
                        or not isinstance(bounds, list) or len(bounds) != 2):
                    continue
                start, end = map(_number, bounds)
                duration = _number(info.get("duration"))
                if start is not None and end is not None and end > start and (duration is None or end <= duration):
                    segments.append({"start": start, "end": end})
        return sorted(segments, key=lambda item: item["start"]), "available" if segments else "no_segments"
    except (httpx.HTTPError, ValueError, TypeError, AttributeError):
        return [], "unavailable"


def _input_options(source, start):
    options = ["-rw_timeout", "15000000"]
    if urlsplit(str(source["url"])).scheme in {"http", "https"}:
        options += ["-reconnect", "1", "-reconnect_on_network_error", "1", "-reconnect_max_retries", "2",
                    "-reconnect_delay_max", "1", "-reconnect_delay_total_max", "2"]
    headers = source.get("http_headers") or {}
    safe = []
    for key, value in headers.items():
        if (not re.fullmatch(r"[A-Za-z0-9-]+", str(key)) or
                any(character in str(value) for character in "\r\n\x00")):
            raise PlaybackError("stream_unavailable")
        safe.append(f"{key}: {value}\r\n")
    if safe:
        options += ["-headers", "".join(safe)]
    if start:
        options += ["-ss", str(start)]
    return options + ["-i", str(source["url"])]


def build_stream_command(ffmpeg, selection, start):
    command = [str(ffmpeg), "-nostdin", "-hide_banner", "-loglevel", "level+info", "-debug_ts"]
    command += _input_options(selection["video"], start)
    if selection["audio"]:
        command += _input_options(selection["audio"], start)
    command += ["-map", "0:v:0", "-map", "1:a:0" if selection["audio"] else "0:a:0",
                "-c", "copy", "-map_metadata", "-1", "-avoid_negative_ts", "make_zero",
                "-movflags", "frag_keyframe+empty_moov+default_base_moof", "-frag_duration", "1000000",
                "-f", "mp4", "pipe:1"]
    return command


def _binary(name):
    directory = Path(os.getenv("DR_DOWNLOAD_FFMPEG", ""))
    executable = directory / (name + ".exe" if os.name == "nt" else name)
    if not directory.is_absolute() or not executable.is_file():
        raise PlaybackError("engine_unavailable", 503)
    return executable


def _creation_flags():
    return subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0


def _packet_time(line, requested):
    if b"demuxer+ffmpeg ->" not in line:
        return None
    try:
        fields = dict(field.split(b":", 1) for field in line.split() if b":" in field)
        actual = requested + float(fields[b"pkt_pts_time"])
        if fields[b"type"] not in (b"video", b"audio"):
            return None
        if not math.isfinite(actual):
            raise ValueError
        return fields[b"type"].decode(), max(0, actual)
    except (ValueError, KeyError):
        raise PlaybackError("stream_unavailable") from None


class PlaybackManager:
    def __init__(self):
        self.sessions = {}
        self.lock = threading.RLock()
        self.pending = set()
        self.closing = False

    def run_process(self, command, *, timeout, capture_output=True, text=False, check=False, creationflags=None):
        with self.lock:
            if self.closing:
                raise PlaybackError("playback_cancelled", 409)
            if len(self.pending) >= 4:
                raise PlaybackError("playback_busy", 429)
            process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                       text=text, creationflags=_creation_flags() if creationflags is None else creationflags)
            self.pending.add(process)
        try:
            try:
                stdout, stderr = process.communicate(timeout=timeout)
            except subprocess.TimeoutExpired:
                _terminate_process_tree(process)
                process.communicate()
                raise
            with self.lock:
                if self.closing:
                    raise PlaybackError("playback_cancelled", 409)
            if check and process.returncode:
                raise subprocess.CalledProcessError(process.returncode, command)
            return subprocess.CompletedProcess(command, process.returncode, stdout, stderr)
        finally:
            with self.lock:
                self.pending.discard(process)
            process.stdout.close()
            process.stderr.close()

    def _verify_stream_codecs(self, info, max_height):
        if info.get("has_drm") or info.get("is_live") or info.get("live_status") in {"is_live", "is_upcoming", "post_live"}:
            return
        formats = info.get("formats") or []
        progressive = sorted((item for item in formats if not item.get("has_drm")
                              and item.get("vcodec") is None and item.get("acodec") is None
                              and item.get("protocol") in {"http", "https"} and item.get("ext") == "mp4"
                              and 0 < (_number(item.get("height")) or 0) <= max_height),
                             key=lambda item: item["height"], reverse=True)
        if not progressive and any(not item.get("has_drm") and item.get("vcodec") == "none" and re.match(r"^(mp4a|aac|opus)", item.get("acodec") or "") for item in formats):
            return
        unknown = [item for item in reversed(formats) if not item.get("has_drm") and item.get("vcodec") == "none" and item.get("acodec") is None and item.get("url")]
        if not progressive and not unknown:
            return
        source = progressive[0] if progressive else unknown[0]
        command = [str(_binary("ffprobe")), "-v", "error"] + _input_options(source, 0)[:-2]
        command += ["-show_entries", "stream=codec_type,codec_name", "-of", "json", source["url"]]
        try:
            result = self.run_process(command, timeout=15)
            if result.returncode:
                if b"skd://" in result.stderr.lower():
                    raise PlaybackError("drm_protected")
                raise ValueError
            tracks = json.loads(result.stdout)["streams"]
            audio = next(item for item in tracks if item.get("codec_type") == "audio")
            if audio.get("codec_name") not in {"aac", "opus"}:
                raise ValueError
            source["acodec"] = audio["codec_name"]
            if progressive:
                video = next(item for item in tracks if item.get("codec_type") == "video")
                if video.get("codec_name") not in {"h264", "vp9", "av1"}:
                    raise ValueError
                source["vcodec"] = video["codec_name"]
        except (subprocess.SubprocessError, ValueError, KeyError, StopIteration):
            raise PlaybackError("stream_unavailable") from None

    def register(self, info, max_height, cookie_source="none"):
        self._verify_stream_codecs(info, max_height)
        selection = select_streams(info, max_height)
        for source in (selection["video"], selection["audio"]):
            if source is not None and urlsplit(source["url"]).scheme not in ("https", "http"):
                raise PlaybackError("stream_unavailable")
        segments, sponsor_status = sponsor_segments(info)
        with self.lock:
            expired = [identifier for identifier, session in self.sessions.items() if session["expires_at"] <= time.monotonic()]
        for identifier in expired:
            self.stop(identifier)
        with self.lock:
            if self.closing:
                raise PlaybackError("playback_cancelled", 409)
            if len(self.sessions) >= 16:
                raise PlaybackError("playback_busy", 429)
            identifier = str(uuid4())
            # Provider expiry can precede our four-hour cap; expire conservatively.
            lifetime = 4 * 60 * 60
            for source in (selection["video"], selection["audio"]):
                if source:
                    expiry = parse_qs(urlsplit(source["url"]).query).get("expire", [])
                    if expiry:
                        try:
                            timestamp = float(expiry[0])
                            if not math.isfinite(timestamp):
                                raise ValueError
                            lifetime = min(lifetime, max(0, timestamp - time.time() - 30))
                        except ValueError:
                            raise PlaybackError("stream_unavailable") from None
            self.sessions[identifier] = {
                "session_id": identifier, "title": str(info.get("title") or "Video")[:500],
                "duration": _number(info.get("duration")), "height": selection["height"],
                "sponsor_segments": segments, "sponsor_status": sponsor_status,
                "actual_start": 0, "status": "buffering", "error": None,
                "selection": selection, "expires_at": time.monotonic() + lifetime,
                "cookie_source": cookie_source, "process": None, "generation": 0, "stream_revision": -1, "stopped": False, "lock": threading.RLock(),
            }
            return self.describe(identifier)

    def _session(self, identifier):
        with self.lock:
            session = self.sessions.get(str(identifier))
        if session is None:
            raise PlaybackError("playback_not_found", 404)
        if session["expires_at"] <= time.monotonic():
            with session["lock"]:
                self._stop_process(session)
            raise PlaybackError("stream_expired", 410)
        return session

    def describe(self, identifier):
        session = self._session(identifier)
        safe = {key: session[key] for key in ("session_id", "title", "duration", "height", "sponsor_status",
                                               "actual_start", "status", "error")}
        safe["sponsor_segments"] = session["sponsor_segments"] if load_config().get("sponsorblock_consent") is True else []
        return safe

    def _stop_process(self, session):
        process = session["process"]
        session["process"] = None
        if process is not None:
            if process.poll() is None:
                _terminate_process_tree(process)
            if process.stdout:
                process.stdout.close()
            reader = getattr(process, "_dr_stderr_thread", None)
            if reader is not None:
                reader.join(timeout=1)
                process.stderr.close()

    def stop(self, identifier):
        with self.lock:
            session = self.sessions.pop(str(identifier), None)
            if session:
                session["stopped"] = True
                session["generation"] += 1
            process = session["process"] if session else None
        if process is not None and process.poll() is None:
            _terminate_process_tree(process)
        if session:
            with session["lock"]:
                self._stop_process(session)

    def shutdown(self):
        with self.lock:
            self.closing = True
            pending = list(self.pending)
            identifiers = list(self.sessions)
        for process in pending:
            if process.poll() is None:
                _terminate_process_tree(process)
        for identifier in identifiers:
            self.stop(identifier)

    def reserve_stream(self, identifier, revision=0):
        if type(revision) is not int or not 0 <= revision <= 2147483647:
            raise PlaybackError("invalid_stream_revision", 422)
        session = self._session(identifier)
        with self.lock:
            if session["stopped"] or self.sessions.get(str(identifier)) is not session or revision < session["stream_revision"]:
                raise PlaybackError("playback_cancelled", 409)
            session["stream_revision"] = revision
            session["generation"] += 1
            generation = session["generation"]
            process = session["process"]
        if process is not None and process.poll() is None:
            _terminate_process_tree(process)
        return generation

    def open_stream(self, identifier, start, generation=None):
        session = self._session(identifier)
        start = validate_start(start, session["duration"])
        if session["cookie_source"] != authorized_cookie_source(session["cookie_source"]):
            raise PlaybackError("browser_consent_required", 403)
        with session["lock"]:
            if session["stopped"] or self.closing or (generation is not None and generation != session["generation"]):
                raise PlaybackError("playback_cancelled", 409)
            self._stop_process(session)
            with self.lock:
                if session["stopped"] or self.closing or (generation is not None and generation != session["generation"]):
                    raise PlaybackError("playback_cancelled", 409)
                process = subprocess.Popen(build_stream_command(_binary("ffmpeg"), session["selection"], start),
                                           stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                           creationflags=_creation_flags())
                session.update(process=process, status="buffering", error=None)
            process._dr_errors = bytearray()
            process._dr_last_times = {}
            timestamp = threading.Event()
            actual = []
            def drain_errors():
                try:
                    while line := process.stderr.readline(65536):
                        if b"[error]" in line or b"[fatal]" in line:
                            process._dr_errors.extend(line)
                            del process._dr_errors[:-65536]
                        try:
                            packet = _packet_time(line, start)
                        except PlaybackError as error:
                            process._dr_errors.extend(error.code.encode() + b"\n")
                            del process._dr_errors[:-65536]
                            timestamp.set()
                            continue
                        if packet is not None:
                            track, value = packet
                            process._dr_last_times[track] = max(value, process._dr_last_times.get(track, 0))
                            if not timestamp.is_set() and track == "video":
                                actual.append(value)
                                timestamp.set()
                finally:
                    timestamp.set()
            process._dr_stderr_thread = threading.Thread(target=drain_errors, daemon=True)
            process._dr_stderr_thread.start()
            timestamp.wait(timeout=15)
            if session["stopped"] or self.closing or (generation is not None and generation != session["generation"]):
                self._stop_process(session)
                raise PlaybackError("playback_cancelled", 409)
            if session["cookie_source"] != authorized_cookie_source(session["cookie_source"]):
                self._stop_process(session)
                raise PlaybackError("browser_consent_required", 403)
            if not actual:
                self.release_stream(session, process)
                detail = session["error"] or {"code": "stream_unavailable", "message": "stream_unavailable"}
                raise PlaybackError(detail["code"], detail=detail)
            session.update(actual_start=actual[0], status="playing")
            return session, process

    def release_stream(self, session, process):
        with session["lock"]:
            if session["process"] is process:
                code = process.poll()
                self._stop_process(session)
                errors = bytes(getattr(process, "_dr_errors", b"")).decode(errors="replace")
                last = getattr(process, "_dr_last_times", {})
                duration = session.get("duration")
                complete = duration is not None and all(last.get(track, -1) >= duration - 0.25 for track in ("video", "audio"))
                transport_only = bool(errors.strip()) and all(any(marker in line.lower() for marker in
                    _TRANSPORT_ERRORS) for line in errors.splitlines() if line.strip())
                if code not in (None, 0) or (errors.strip() and not (complete and transport_only)):
                    detail = classify_error("network connection" if transport_only else errors)
                    if detail["code"] == "engine_error":
                        detail = {"code": "stream_unavailable", "message": "stream_unavailable"}
                    session.update(status="failed", error=detail)
                else:
                    session["status"] = "ended"

    async def stream(self, session, process):
        try:
            while True:
                chunk = await asyncio.to_thread(process.stdout.read1, 64 * 1024)
                if not chunk:
                    await asyncio.to_thread(process.wait, timeout=5)
                    break
                yield chunk
        finally:
            # Cancellation closes the pipe and kills only this stream's owned process.
            with anyio.CancelScope(shield=True):
                await asyncio.to_thread(self.release_stream, session, process)


manager = PlaybackManager()


def start_playback(url, cookie_source, max_height):
    validate_provider_url(url)
    if cookie_source not in {"none", "edge", "firefox"}:
        raise PlaybackError("source_unsupported", 422)
    if cookie_source != authorized_cookie_source(cookie_source):
        raise PlaybackError("browser_consent_required", 403)
    try:
        info = inspect_with_engine(resolve_engine(), url, cookie_source, run_process=manager.run_process)
        if cookie_source != authorized_cookie_source(cookie_source):
            raise PlaybackError("browser_consent_required", 403)
        return manager.register(info, max_height, cookie_source)
    except PlaybackError:
        raise
    except Exception as error:
        detail = classify_error(str(error), cookie_source)
        raise PlaybackError(detail["code"], 400, detail) from None
