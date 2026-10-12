"""Local playlists and bounded, cancellable imports through the included engine."""

from __future__ import annotations

import json
import math
import os
import re
import sqlite3
import subprocess
import threading
import time
from collections import OrderedDict
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import urlsplit
from uuid import UUID

from fastapi import APIRouter, HTTPException, Response
from pydantic import BaseModel, StrictStr

from .config import authorized_cookie_source
from .engine_runner import _terminate_process_tree, node_runtime_argument, resolve_engine
from .error_mapping import classify_error

router = APIRouter()
_imports_lock = threading.RLock()
_imports: OrderedDict[str, ImportJob] = OrderedDict()


@dataclass
class ImportJob:
    cancelled: threading.Event = field(default_factory=threading.Event)
    process: Any = None
    active: bool = False
    committed: bool = False
    created: float = field(default_factory=time.monotonic)


class PlaylistName(BaseModel):
    name: StrictStr


class PlaylistItem(BaseModel):
    url: StrictStr
    title: StrictStr | None = None
    duration: Any = None
    thumbnail: StrictStr | None = None


class PlaylistImport(BaseModel):
    request_id: UUID
    url: StrictStr
    cookie_source: StrictStr = "none"


def _error(code: str, status: int = 400, **extra):
    raise HTTPException(status_code=status, detail={
        "code": code,
        "message": "No se pudo completar la operación de la lista.",
        "recovery": "Revisa los datos o vuelve a intentarlo.",
        **extra,
    })


def validate_provider_url(value: str) -> str:
    if not isinstance(value, str) or not 8 <= len(value) <= 2048 or any(c.isspace() or ord(c) < 32 or ord(c) == 127 for c in value):
        _error("unsupported_provider")
    try:
        parsed = urlsplit(value)
        host = (parsed.hostname or "").lower()
        allowed = any(host == provider or host.endswith("." + provider) for provider in ("youtube.com", "youtu.be", "vimeo.com"))
        if parsed.scheme != "https" or not allowed or parsed.username is not None or parsed.password is not None or parsed.port not in (None, 443) or parsed.fragment:
            _error("unsupported_provider")
    except ValueError:
        _error("unsupported_provider")
    return value


def _name(value: str) -> str:
    name = value.strip()
    if not 1 <= len(name) <= 100 or any(ord(c) < 32 for c in name):
        _error("invalid_playlist_name")
    return name


def _thumbnail(value: Any) -> str | None:
    if not isinstance(value, str) or len(value) > 2048 or any(c.isspace() for c in value):
        return None
    try:
        parsed = urlsplit(value)
        host = (parsed.hostname or "").lower()
        allowed = any(host == provider or host.endswith("." + provider) for provider in ("ytimg.com", "ggpht.com", "vimeocdn.com"))
        if parsed.scheme == "https" and allowed and not parsed.username and not parsed.password and not parsed.query and not parsed.fragment and parsed.port in (None, 443):
            return value
    except ValueError:
        return None
    return None


def _item(url: str, title: Any = None, duration: Any = None, thumbnail: Any = None, available: bool = True) -> dict:
    if duration is not None and (isinstance(duration, bool) or not isinstance(duration, (int, float)) or not math.isfinite(duration) or duration < 0):
        _error("invalid_playlist_metadata")
    safe_title = "".join(c for c in title if ord(c) >= 32)[:500].strip() if isinstance(title, str) else ""
    return {"url": validate_provider_url(url), "title": safe_title or url, "duration": duration,
            "thumbnail": _thumbnail(thumbnail), "available": available}


def get_store():
    from .downloader import _store
    return _store


def _store_call(method: str, *args):
    try:
        return getattr(get_store(), method)(*args)
    except (sqlite3.Error, OSError):
        _error("playlist_storage_unavailable", 503)


@router.get("/playlists")
def list_playlists():
    return _store_call("list_playlists")


@router.post("/playlists")
def create_playlist(request: PlaylistName):
    return _store_call("create_playlist", _name(request.name))


def _prune_imports():
    now = time.monotonic()
    for request_id, job in list(_imports.items()):
        if not job.active and now - job.created > 300:
            del _imports[request_id]
    # Keep cancellation tombstones bounded without evicting live jobs.
    if len(_imports) >= 256:
        _error("playlist_import_busy", 503)


def _take_process(job: ImportJob):
    with _imports_lock:
        process, job.process = job.process, None
        return process


def _stop_process(process):
    if process is not None and process.poll() is None:
        _terminate_process_tree(process)


def _check_cancelled(job: ImportJob):
    if job.cancelled.is_set():
        _error("playlist_import_cancelled", 409)


def _check_consent(cookie_source: str):
    if cookie_source not in {"none", "edge", "firefox"}:
        _error("unsupported_cookie_source")
    if authorized_cookie_source(cookie_source) != cookie_source:
        raise HTTPException(status_code=403, detail=classify_error("Browser consent required"))


def _extract_playlist(url: str, cookie_source: str, job: ImportJob) -> dict:
    command = [str(resolve_engine()), "--ignore-config", "--no-warnings", "--flat-playlist",
               "--dump-single-json", "--playlist-end", "501", "--ignore-errors",
               "--socket-timeout", "15", "--js-runtimes", node_runtime_argument()]
    output = bytearray()
    exceeded = threading.Event()

    def read_output(pipe, capture):
        try:
            while chunk := pipe.read(65536):
                if capture:
                    if len(output) + len(chunk) > 8 * 1024 * 1024:
                        exceeded.set()
                        return
                    output.extend(chunk)
        except (OSError, ValueError):
            exceeded.set()

    with _imports_lock:
        _check_cancelled(job)
        _check_consent(cookie_source)
        if cookie_source != "none":
            command += ["--cookies-from-browser", cookie_source]
        process = subprocess.Popen(command + ["--", url], stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                   shell=False, creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
        job.process = process
    readers = [threading.Thread(target=read_output, args=(process.stdout, True), daemon=True),
               threading.Thread(target=read_output, args=(process.stderr, False), daemon=True)]
    for reader in readers:
        reader.start()
    deadline = time.monotonic() + 60
    try:
        while process.poll() is None:
            _check_cancelled(job)
            if exceeded.is_set():
                _error("playlist_import_invalid")
            if time.monotonic() >= deadline:
                _error("playlist_import_timeout", 504)
            job.cancelled.wait(0.05)
        for reader in readers:
            reader.join(timeout=2)
        _check_cancelled(job)
        if exceeded.is_set() or any(reader.is_alive() for reader in readers):
            _error("playlist_import_invalid")
        if process.returncode:
            _error("playlist_import_failed")
        data = json.loads(output.decode("utf-8"))
        if not isinstance(data, dict) or not isinstance(data.get("entries"), list):
            _error("playlist_import_invalid")
        return data
    finally:
        _stop_process(_take_process(job))
        for reader in readers:
            reader.join(timeout=2)
        process.stdout.close()
        process.stderr.close()


def _import_items(data: dict, source: str) -> list[dict]:
    entries = data.get("entries")
    if not isinstance(entries, list):
        _error("playlist_import_invalid")
    count = data.get("playlist_count") or data.get("n_entries") or len(entries)
    if len(entries) > 500 or isinstance(count, (int, float)) and count > 500:
        _error("playlist_too_large", found=max(len(entries), count) if isinstance(count, (int, float)) else len(entries))
    items = []
    is_youtube = "vimeo.com" not in (urlsplit(source).hostname or "")
    for entry in entries:
        entry = entry if isinstance(entry, dict) else {}
        url = entry.get("webpage_url") or entry.get("url")
        try:
            validate_provider_url(url)
        except HTTPException:
            identity = entry.get("id")
            if isinstance(identity, str) and re.fullmatch(r"[A-Za-z0-9_-]{1,100}", identity):
                url = f"https://www.youtube.com/watch?v={identity}" if is_youtube else f"https://vimeo.com/{identity}"
            else:
                url = source
        title = entry.get("title")
        available = bool(entry) and url != source and entry.get("availability") not in {"private", "needs_auth", "premium_only", "subscriber_only", "unavailable"} and title not in {"[Private video]", "[Deleted video]"}
        duration = entry.get("duration")
        if isinstance(duration, bool) or not isinstance(duration, (int, float)) or not math.isfinite(duration) or duration < 0:
            duration = None
        items.append(_item(url, title or ("Unavailable video" if not available else None), duration, entry.get("thumbnail"), available))
    return items


@router.post("/playlists/import")
def import_playlist(request: PlaylistImport):
    source = validate_provider_url(request.url)
    _check_consent(request.cookie_source)
    request_id = str(request.request_id)
    with _imports_lock:
        previous = _imports.get(request_id)
        if previous:
            _check_cancelled(previous)
            _error("playlist_import_conflict", 409)
        _prune_imports()
        if sum(job.active for job in _imports.values()) >= 4:
            _error("playlist_import_busy", 503)
        job = ImportJob(active=True)
        _imports[request_id] = job
    try:
        data = _extract_playlist(source, request.cookie_source, job)
        items = _import_items(data, source)
        title = data.get("title")
        name = "".join(c for c in title if ord(c) >= 32).strip()[:100] if isinstance(title, str) else ""
        with _imports_lock:
            # Cancellation and the complete SQLite commit share one ordering point.
            _check_cancelled(job)
            _check_consent(request.cookie_source)
            playlist = _store_call("create_playlist", name or "Imported playlist", items)
            job.committed = True
            return {"playlist": playlist, "imported": len(items), "unavailable": sum(not item["available"] for item in items)}
    except HTTPException:
        raise
    except (OSError, RuntimeError, ValueError, TypeError):
        _error("playlist_import_failed")
    finally:
        with _imports_lock:
            job.active = False
        _stop_process(_take_process(job))


@router.delete("/playlists/import/{request_id}", status_code=204)
def cancel_playlist_import(request_id: UUID):
    with _imports_lock:
        key = str(request_id)
        job = _imports.get(key)
        if job is not None and job.committed:
            _error("playlist_import_completed", 409)
        if job is None:
            _prune_imports()
            job = ImportJob()
            _imports[key] = job
        job.cancelled.set()
    _stop_process(_take_process(job))
    return Response(status_code=204)


def shutdown_imports():
    with _imports_lock:
        jobs = list(_imports.values())
        for job in jobs:
            job.cancelled.set()
        for key in [key for key, job in _imports.items() if not job.active]:
            del _imports[key]
    for job in jobs:
        _stop_process(_take_process(job))


@router.put("/playlists/{playlist_id}")
def rename_playlist(playlist_id: UUID, request: PlaylistName):
    return _store_call("rename_playlist", str(playlist_id), _name(request.name)) or _error("playlist_not_found", 404)


@router.delete("/playlists/{playlist_id}", status_code=204)
def delete_playlist(playlist_id: UUID):
    if not _store_call("delete_playlist", str(playlist_id)):
        _error("playlist_not_found", 404)
    return Response(status_code=204)


@router.post("/playlists/{playlist_id}/items")
def add_playlist_item(playlist_id: UUID, request: PlaylistItem):
    item = _item(request.url, request.title, request.duration, request.thumbnail)
    return _store_call("add_playlist_item", str(playlist_id), item) or _error("playlist_not_found", 404)


@router.delete("/playlists/{playlist_id}/items/{item_id}", status_code=204)
def remove_playlist_item(playlist_id: UUID, item_id: UUID):
    if not _store_call("remove_playlist_item", str(playlist_id), str(item_id)):
        _error("playlist_item_not_found", 404)
    return Response(status_code=204)
