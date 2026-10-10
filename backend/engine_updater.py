"""Verified, recoverable updater for the standalone yt-dlp engine."""

import hashlib
import logging
import os
import subprocess
import threading
import time
import urllib.request
from pathlib import Path
from typing import Callable


RELEASE_BASE = "https://github.com/yt-dlp/yt-dlp/releases/latest/download"


def parse_sha256(content: str, asset: str) -> str:
    for line in content.splitlines():
        parts = line.strip().split()
        if len(parts) >= 2 and parts[-1].lstrip("*") == asset:
            return parts[0].lower()
    raise ValueError(f"No checksum published for {asset}")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def install_verified(
    candidate: str | Path,
    target: str | Path,
    expected_sha256: str,
    health_check: Callable[[Path], bool] | None = None,
) -> None:
    source = Path(candidate)
    destination = Path(target)
    if _sha256(source) != expected_sha256.lower():
        raise ValueError("Engine checksum verification failed")
    if health_check and not health_check(source):
        raise ValueError("Engine health check failed")

    destination.parent.mkdir(parents=True, exist_ok=True)
    previous = destination.with_suffix(destination.suffix + ".previous")
    if previous.exists():
        previous.unlink()
    if destination.exists():
        os.replace(destination, previous)
    try:
        os.replace(source, destination)
    except Exception:
        if previous.exists() and not destination.exists():
            os.replace(previous, destination)
        raise


def _download(url: str, target: Path) -> None:
    request = urllib.request.Request(url, headers={"User-Agent": "DrDownload/2.1"})
    with urllib.request.urlopen(request, timeout=30) as response, target.open("wb") as output:
        while chunk := response.read(1024 * 1024):
            output.write(chunk)


def _healthy(path: Path) -> bool:
    result = subprocess.run(
        [str(path), "--version"], capture_output=True, timeout=15, check=False,
        creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
    )
    return result.returncode == 0 and bool(result.stdout.strip())


def update_if_due(data_dir: str | Path, minimum_interval: int = 86_400) -> Path | None:
    """Update at most once per interval; an update failure leaves the app usable."""
    directory = Path(data_dir) / "engine"
    directory.mkdir(parents=True, exist_ok=True)
    marker = directory / "last-check"
    if marker.exists() and time.time() - marker.stat().st_mtime < minimum_interval:
        return directory / "yt-dlp.exe" if (directory / "yt-dlp.exe").exists() else None
    marker.touch()
    candidate = directory / "yt-dlp.download"
    try:
        sums_request = urllib.request.Request(
            f"{RELEASE_BASE}/SHA2-256SUMS", headers={"User-Agent": "DrDownload/2.1"}
        )
        with urllib.request.urlopen(sums_request, timeout=30) as response:
            expected = parse_sha256(response.read().decode("utf-8"), "yt-dlp.exe")
        _download(f"{RELEASE_BASE}/yt-dlp.exe", candidate)
        install_verified(candidate, directory / "yt-dlp.exe", expected, _healthy)
        return directory / "yt-dlp.exe"
    except Exception as exc:
        logging.warning("yt-dlp update skipped: %s", type(exc).__name__)
        if candidate.exists():
            candidate.unlink()
        return directory / "yt-dlp.exe" if (directory / "yt-dlp.exe").exists() else None


def start_background_update(data_dir: str | Path, enabled: bool = True):
    if not enabled:
        return None
    thread = threading.Thread(
        target=update_if_due, args=(data_dir,), daemon=True, name="yt-dlp-updater"
    )
    thread.start()
    return thread


def ensure_engine_ready(data_dir: str | Path, updates_enabled: bool = True) -> Path:
    """Require one healthy engine before the API begins accepting work."""
    root = Path(data_dir)
    engine = root / "engine" / "yt-dlp.exe"
    if engine.is_file() and _healthy(engine):
        start_background_update(root, updates_enabled)
        return engine
    if not updates_enabled:
        raise RuntimeError("yt-dlp engine is unavailable")
    installed = update_if_due(root, minimum_interval=0)
    if not installed or not installed.is_file() or not _healthy(installed):
        raise RuntimeError("yt-dlp engine is unavailable")
    return installed
