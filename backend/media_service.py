"""Normalize media inspection data from the external engine."""

from typing import Any

from .engine_runner import inspect_with_engine, resolve_engine
from .error_mapping import is_browser_cookie_error


COOKIE_SOURCES = {"none", "edge", "firefox"}


def normalize_info(info: dict[str, Any]) -> dict[str, Any]:
    """Return the small, stable metadata contract consumed by the desktop UI."""
    formats: list[dict[str, Any]] = []
    seen: set[tuple[str, int | None]] = set()
    for item in info.get("formats") or []:
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
                "estimated_bytes": item.get("filesize") or item.get("filesize_approx"),
            }
        )

    presets = [
        {"id": "video-best", "kind": "video", "label": "Mejor calidad", "container": "mp4"},
        {"id": "audio-mp3", "kind": "audio", "label": "MP3 · 192 kbps", "container": "mp3"},
        {"id": "audio-original", "kind": "audio", "label": "Audio original", "container": None},
    ]
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
    engine = resolve_engine()
    try:
        return normalize_info(inspect_with_engine(engine, url, cookie_source))
    except RuntimeError as exc:
        # A locked/unreadable cookie store must not block inspecting public media.
        if cookie_source != "none" and is_browser_cookie_error(str(exc)):
            return normalize_info(inspect_with_engine(engine, url, "none"))
        raise
