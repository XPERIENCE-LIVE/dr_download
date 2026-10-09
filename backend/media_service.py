"""Normalize media inspection data from the external engine."""

import math
from typing import Any

from .engine_runner import inspect_with_engine, resolve_engine
from .error_mapping import is_browser_cookie_error
from .config import authorized_cookie_source


COOKIE_SOURCES = {"none", "edge", "firefox"}


def _estimated_bytes(item: dict[str, Any] | None, audio: dict[str, Any] | None = None) -> int | None:
    if not item:
        return None
    size = item.get("filesize") or item.get("filesize_approx")
    if type(size) is not int or not 0 < size <= 9007199254740991:
        return None
    if item.get("vcodec") not in (None, "none") and item.get("acodec") in (None, "none"):
        audio_size = _estimated_bytes(audio)
        if audio_size is None:
            return None
        size += audio_size
    return size if size <= 9007199254740991 else None


def normalize_info(info: dict[str, Any]) -> dict[str, Any]:
    """Return the small, stable metadata contract consumed by the desktop UI."""
    # yt-dlp inspection orders formats from worst to best, including codec preference.
    sources = info.get("formats") or []
    video = [item for item in sources if item.get("vcodec") not in (None, "none", "images") and item.get("ext") != "mhtml"]
    audio = [item for item in sources if item.get("vcodec") == "none" and item.get("acodec") not in (None, "none")]
    muxed = [item for item in video if item.get("acodec") not in (None, "none")]
    m4a = [item for item in audio if item.get("ext") == "m4a"]
    best_audio = audio[-1] if audio else (muxed[-1] if muxed else None)
    merge_audio = m4a[-1] if m4a else (audio[-1] if audio else None)
    h264 = [item for item in video if str(item.get("vcodec")).startswith(("avc1", "avc3", "h264"))]
    aac = [item for item in m4a if str(item.get("acodec")).startswith(("mp4a", "aac"))]
    compatible_video = [item for item in h264 if item.get("acodec") == "none"]
    compatible_muxed = [item for item in h264 if str(item.get("acodec")).startswith(("mp4a", "aac"))]
    compatible = compatible_video[-1] if compatible_video and aac else (compatible_muxed[-1] if compatible_muxed else None)
    audio_size = _estimated_bytes(best_audio)
    duration = info.get("duration")
    mp3_size = None
    if audio_size is not None and type(duration) in (int, float) and 0 < duration <= 9007199254740991 / 24000:
        mp3_size = max(audio_size, math.ceil(duration * 24000))
    formats: list[dict[str, Any]] = []
    seen: set[tuple[str, int | None]] = set()
    for item in sources:
        if item.get("ext") == "mhtml" or (
            item.get("vcodec") in (None, "none")
            and item.get("acodec") in (None, "none")
        ):
            continue
        has_video = item.get("vcodec") not in (None, "none")
        kind = "video" if has_video else "audio"
        value = item.get("height") if has_video else item.get("abr")
        key = (kind, value)
        if key in seen:
            continue
        seen.add(key)
        if has_video:
            label = f"{value}p" if value else "Video"
        else:
            label = f"{round(value)} kbps" if value else "Audio original"
        formats.append(
            {
                "id": str(item.get("format_id", "best")),
                "kind": kind,
                "label": label,
                "container": item.get("ext"),
                "height": item.get("height"),
                "bitrate_kbps": item.get("abr") or item.get("tbr"),
                "estimated_bytes": _estimated_bytes(item, merge_audio),
            }
        )

    presets = [
        {"id": "video-compatible", "kind": "video", "label": "MP4 compatible · H.264 + AAC", "container": "mp4", "estimated_bytes": _estimated_bytes(compatible, aac[-1] if aac else None)},
        {"id": "video-best", "kind": "video", "label": "Mejor calidad", "container": "mp4"},
        {"id": "audio-mp3", "kind": "audio", "label": "MP3 · 192 kbps", "container": "mp3"},
        {"id": "audio-original", "kind": "audio", "label": "Audio original", "container": None},
    ]
    presets[1]["estimated_bytes"] = _estimated_bytes(video[-1] if video else None, merge_audio)
    presets[2]["estimated_bytes"] = mp3_size
    presets[3]["estimated_bytes"] = audio_size
    for preset in presets:
        preset["preset"] = True
    return {
        "title": info.get("title") or "Sin título",
        "author": info.get("uploader") or info.get("channel") or "Autor desconocido",
        "duration": info.get("duration"),
        "thumbnail": info.get("thumbnail"),
        "formats": presets + formats,
    }


def inspect_media(url: str, cookie_source: str = "none") -> dict[str, Any]:
    """Inspect a URL without downloading its media."""
    if cookie_source not in COOKIE_SOURCES:
        raise ValueError("Unsupported cookie source")
    if cookie_source != authorized_cookie_source(cookie_source):
        raise PermissionError("Browser consent required")
    engine = resolve_engine()
    try:
        return normalize_info(inspect_with_engine(engine, url, cookie_source))
    except RuntimeError as exc:
        # A locked/unreadable cookie store must not block inspecting public media.
        if cookie_source != "none" and is_browser_cookie_error(str(exc)):
            return normalize_info(inspect_with_engine(engine, url, "none"))
        raise
