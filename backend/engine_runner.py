"""Subprocess adapter for the independently updatable yt-dlp executable."""

import json
import os
import re
import shutil
import subprocess
import uuid
from pathlib import Path
from typing import Callable

from .error_mapping import is_browser_cookie_error
from .config import authorized_cookie_source


PROGRESS_PREFIX = "__DR_PROGRESS__"
FILE_PREFIX = "__DR_FILE__"
TRANSIENT_ATTEMPTS = 3
FORMAT_ID_PATTERN = r"^[A-Za-z0-9_.:-]{1,128}$"


def resolve_node_path() -> str | None:
    value = os.getenv("DR_DOWNLOAD_NODE")
    return str(Path(value)) if value and Path(value).is_file() else None


def node_runtime_argument() -> str:
    path = resolve_node_path()
    if not path:
        raise RuntimeError("Node runtime is unavailable")
    return f"node:{path}"


def resolve_engine() -> Path:
    explicit = os.getenv("DR_DOWNLOAD_YTDLP")
    if explicit:
        engine = Path(explicit)
        if not engine.is_file():
            raise RuntimeError("yt-dlp engine is unavailable")
        return engine
    data_dir = os.getenv("DR_DOWNLOAD_DATA_DIR")
    candidate = Path(data_dir) / "engine" / "yt-dlp.exe" if data_dir else None
    if not candidate or not candidate.is_file():
        raise RuntimeError("yt-dlp engine is unavailable")
    return candidate


def build_command(
    executable: str | Path,
    url: str,
    format_id: str,
    output_dir: str,
    cookie_source: str,
) -> list[str]:
    command = [
        # --print implies --quiet, which hides progress; --progress brings it back.
        str(executable), "--no-playlist", "--newline", "--progress", "--js-runtimes", node_runtime_argument(),
        "--progress-template", f"download:{PROGRESS_PREFIX}%(progress._percent_str)s|%(progress.downloaded_bytes)s|%(progress.total_bytes_estimate)s|%(progress.speed)s|%(progress.eta)s",
        "--print", f"after_move:{FILE_PREFIX}%(filepath)s",
        "--output", str(Path(output_dir) / "%(title)s.%(ext)s"),
        # Titles can be whole post descriptions (TikTok, X); NTFS rejects names
        # over 255 chars, and 150 keeps the full path under Windows' 260 limit
        # for typical folders.
        "--trim-filenames", "150",
    ]
    ffmpeg = os.getenv("DR_DOWNLOAD_FFMPEG")
    if ffmpeg:
        # On a missing location yt-dlp "continues without ffmpeg": video and
        # audio are never merged and the user silently gets a mute video.
        if not any((Path(ffmpeg) / name).is_file() for name in ("ffmpeg.exe", "ffmpeg")):
            raise RuntimeError("FFmpeg is unavailable")
        command += ["--ffmpeg-location", ffmpeg]
    cookie_source = authorized_cookie_source(cookie_source)
    if cookie_source != "none":
        command += ["--cookies-from-browser", cookie_source]
    # Prefer AAC (m4a) audio: YouTube's "best" audio is Opus, which Windows
    # players, TVs and editors play silently inside an MP4.
    if format_id == "video-best":
        command += ["--format", "bv*+ba[ext=m4a]/bv*+ba/b", "--merge-output-format", "mp4"]
    elif format_id == "video-compatible":
        # Every branch requires H.264 and AAC; remux also covers already-muxed sources.
        command += [
            "--format", "bv[vcodec~='^(avc1|avc3|h264)']+ba[ext=m4a][acodec~='^(mp4a|aac)']/b[vcodec~='^(avc1|avc3|h264)'][acodec~='^(mp4a|aac)']",
            "--merge-output-format", "mp4", "--remux-video", "mp4",
        ]
    elif format_id == "audio-mp3":
        command += ["--format", "bestaudio/best", "--extract-audio", "--audio-format", "mp3", "--audio-quality", "192K"]
    elif format_id == "audio-original":
        command += ["--format", "bestaudio/best"]
    elif isinstance(format_id, str) and re.fullmatch(FORMAT_ID_PATTERN, format_id):
        # A concrete stream chosen from the inspect list. Merge best audio so
        # video-only streams keep sound; yt-dlp's default no-audio-multistreams
        # leaves audio-only or already-muxed streams untouched. Works for the
        # string format ids used by non-YouTube extractors, not just digits.
        selected = str(format_id)
        command += ["--format", f"{selected}+ba[ext=m4a]/{selected}+bestaudio/{selected}"]
    else:
        raise ValueError("Unsupported format")
    command.append(url)
    return command


def _number(value: str, integer: bool = True):
    match = re.search(r"[\d.]+", value or "")
    if not match:
        return None
    number = float(match.group())
    return int(number) if integer else number


def parse_progress(line: str) -> dict | None:
    if PROGRESS_PREFIX not in line:
        return None
    values = line.split(PROGRESS_PREFIX, 1)[1].strip().split("|")
    if len(values) != 5:
        return None
    return {
        "progress": _number(values[0]) or 0,
        "bytes_downloaded": _number(values[1]) or 0,
        "total_bytes": _number(values[2]) or None,
        "speed_bps": _number(values[3]) or None,
        "eta_seconds": _number(values[4]) or None,
    }


def _terminate_process_tree(process) -> None:
    if os.name == "nt" and getattr(process, "pid", None):
        subprocess.run(
            ["taskkill", "/PID", str(process.pid), "/T", "/F"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
            shell=False,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        process.wait(timeout=10)
        return
    process.terminate()
    try:
        process.wait(timeout=10)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=10)


def inspect_with_engine(executable: str | Path, url: str, cookie_source: str) -> dict:
    command = [
        str(executable),
        "--dump-single-json",
        "--no-playlist",
        "--no-warnings",
        "--js-runtimes",
        node_runtime_argument(),
    ]
    cookie_source = authorized_cookie_source(cookie_source)
    if cookie_source != "none":
        command += ["--cookies-from-browser", cookie_source]
    command.append(url)
    result = subprocess.run(
        command, capture_output=True, text=True, timeout=90, check=False,
        creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
    )
    if result.returncode:
        raise RuntimeError(result.stderr.strip() or "Media inspection failed")
    return json.loads(result.stdout)


# yt-dlp replaces the chars Windows forbids in filenames (/ \ : * ? " < > |)
# with full-width Unicode lookalikes. Map them to plain standard characters.
_LOOKALIKES = str.maketrans({
    "⧸": "-", "⧹": "-", "｜": "-", "：": "-",
    "＊": "", "？": "", "＂": "'", "＜": "(", "＞": ")",
})


def standard_filename(name: str) -> str:
    path = Path(name)
    stem = path.stem.replace("： ", " - ").translate(_LOOKALIKES)
    # Windows also rejects names ending in a dot or space.
    stem = re.sub(r"\s+", " ", stem).strip(" .")
    return f"{stem or 'download'}{path.suffix}"


def unique_destination(dest_dir: Path, name: str) -> Path:
    """Return dest_dir/name, adding a ' (n)' suffix so an existing file is never
    overwritten (Chrome-style). Prevents clobbering the user's library."""
    target = dest_dir / name
    if not target.exists():
        return target
    stem, suffix = target.stem, target.suffix
    index = 1
    while (dest_dir / f"{stem} ({index}){suffix}").exists():
        index += 1
    return dest_dir / f"{stem} ({index}){suffix}"


def download_with_engine(
    executable: str | Path,
    url: str,
    format_id: str,
    output_dir: str,
    cookie_source: str,
    on_progress: Callable[[dict], None],
    cancelled,
) -> str | None:
    # Download into an empty staging dir on the destination volume. yt-dlp skips
    # ("already downloaded") when the target exists, so downloading straight into
    # the user's folder silently no-ops on a name collision. Staging guarantees
    # the download always runs; the finished file is then moved beside its peers
    # with a collision-safe name.
    destination = Path(output_dir)
    staging = destination / f".dr-download-{uuid.uuid4().hex}"
    staging.mkdir(parents=True, exist_ok=True)
    try:
        process = subprocess.Popen(
            build_command(executable, url, format_id, str(staging), cookie_source),
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace",
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
        )
        filename = None
        tail: list[str] = []
        assert process.stdout is not None
        for raw in process.stdout:
            if cancelled.is_set():
                _terminate_process_tree(process)
                raise RuntimeError("Download cancelled")
            line = raw.strip()
            tail = (tail + [line])[-8:]
            progress = parse_progress(line)
            if progress:
                on_progress(progress)
            elif line.startswith(FILE_PREFIX):
                filename = line[len(FILE_PREFIX):]
        code = process.wait()
        if code:
            raise RuntimeError("\n".join(tail) or "Download failed")
        # yt-dlp's stdout uses the console code page on Windows, so a printed
        # path drops chars like the "⧸" it substitutes for "/" in titles. The
        # staging dir is private to this download: trust what is on disk.
        produced = Path(filename) if filename else None
        if not produced or not produced.is_file():
            files = [p for p in staging.iterdir() if p.is_file()]
            if not files:
                return None
            produced = max(files, key=lambda p: p.stat().st_mtime)
        final = unique_destination(destination, standard_filename(produced.name))
        os.replace(produced, final)  # same volume as staging → atomic rename
        return str(final)
    finally:
        shutil.rmtree(staging, ignore_errors=True)


def download_with_cookie_fallback(
    executable: str | Path,
    url: str,
    format_id: str,
    output_dir: str,
    cookie_source: str,
    on_progress: Callable[[dict], None],
    cancelled,
) -> str | None:
    """Download using browser cookies, but never let a locked cookie store block
    public content: if reading cookies fails, retry once without them. YouTube
    also intermittently answers 403 on stream URLs; a fresh run gets new URLs."""
    for attempt in range(TRANSIENT_ATTEMPTS):
        try:
            return download_with_engine(
                executable, url, format_id, output_dir, cookie_source, on_progress, cancelled
            )
        except RuntimeError as exc:
            if cancelled.is_set() or attempt == TRANSIENT_ATTEMPTS - 1:
                raise
            if cookie_source != "none" and is_browser_cookie_error(str(exc)):
                cookie_source = "none"
            elif "HTTP Error 403" not in str(exc):
                raise
