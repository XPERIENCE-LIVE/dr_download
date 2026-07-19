"""Subprocess adapter for the independently updatable yt-dlp executable."""

import json
import os
import re
import subprocess
from pathlib import Path
from typing import Callable


PROGRESS_PREFIX = "__DR_PROGRESS__"
FILE_PREFIX = "__DR_FILE__"


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
        str(executable), "--no-playlist", "--newline", "--js-runtimes", node_runtime_argument(),
        "--progress-template", f"download:{PROGRESS_PREFIX}%(progress._percent_str)s|%(progress.downloaded_bytes)s|%(progress.total_bytes_estimate)s|%(progress.speed)s|%(progress.eta)s",
        "--print", f"after_move:{FILE_PREFIX}%(filepath)s",
        "--output", str(Path(output_dir) / "%(title)s.%(ext)s"),
    ]
    ffmpeg = os.getenv("DR_DOWNLOAD_FFMPEG")
    if ffmpeg:
        command += ["--ffmpeg-location", ffmpeg]
    if cookie_source != "none":
        command += ["--cookies-from-browser", cookie_source]
    if format_id == "video-best":
        command += ["--format", "bv*+ba/b", "--merge-output-format", "mp4"]
    elif format_id == "audio-mp3":
        command += ["--format", "bestaudio/best", "--extract-audio", "--audio-format", "mp3", "--audio-quality", "192K"]
    elif format_id == "audio-original":
        command += ["--format", "bestaudio/best"]
    elif str(format_id).isdigit():
        command += ["--format", str(format_id)]
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


def download_with_engine(
    executable: str | Path,
    url: str,
    format_id: str,
    output_dir: str,
    cookie_source: str,
    on_progress: Callable[[dict], None],
    cancelled,
) -> str | None:
    process = subprocess.Popen(
        build_command(executable, url, format_id, output_dir, cookie_source),
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
    return filename
