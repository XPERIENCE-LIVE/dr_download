"""Live smoke test for Dr. Download's real media pipeline."""

import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.downloader import enqueue_premium_download, get_download, shutdown_workers
from backend.media_service import inspect_media


def main() -> int:
    parser = argparse.ArgumentParser(description="Inspect or download one authorized media URL")
    parser.add_argument("url")
    parser.add_argument("--mode", choices=("inspect", "audio", "video"), default="inspect")
    parser.add_argument("--cookie-source", choices=("none", "edge", "firefox"), default="none")
    parser.add_argument("--output", type=Path, default=Path.home() / "Downloads")
    parser.add_argument("--timeout", type=int, default=900)
    args = parser.parse_args()

    metadata = inspect_media(args.url, args.cookie_source)
    print(json.dumps({key: metadata.get(key) for key in ("title", "author", "duration")}, ensure_ascii=False))
    if args.mode == "inspect":
        return 0

    args.output.mkdir(parents=True, exist_ok=True)
    started = time.time()
    task = enqueue_premium_download(
        args.url,
        "audio-mp3" if args.mode == "audio" else "video-best",
        str(args.output),
        args.cookie_source,
    )
    last_status = None
    try:
        while time.time() - started < args.timeout:
            current = get_download(task["id"])
            if current and current.get("status") != last_status:
                last_status = current.get("status")
                print(json.dumps(current, ensure_ascii=False, default=str))
            if current and current.get("status") in {"completed", "failed", "cancelled"}:
                if current["status"] != "completed":
                    return 2
                filename = current.get("filename")
                candidates = [Path(filename)] if filename else []
                candidates += [path for path in args.output.iterdir() if path.is_file() and path.stat().st_mtime >= started]
                valid = next((path for path in candidates if path.exists() and path.stat().st_size > 0), None)
                if not valid:
                    print("Download reported completion but no non-empty file was found", file=sys.stderr)
                    return 3
                print(json.dumps({"verified_file": str(valid), "bytes": valid.stat().st_size}, ensure_ascii=False))
                return 0
            time.sleep(1)
        print("Timed out waiting for download", file=sys.stderr)
        return 4
    finally:
        shutdown_workers()


if __name__ == "__main__":
    raise SystemExit(main())
