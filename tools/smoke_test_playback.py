"""Real-provider playback smoke; isolated backend, bundled tools, no mocks.

Run from the repository root. Evidence is not installed-Windows acceptance.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import platform
import socket
import subprocess
import sys
import time
from uuid import uuid4

import httpx

ROOT = Path(__file__).resolve().parents[1]


def decoded_track_summary(frames):
    result = {}
    for kind in ("video", "audio"):
        times = [float(frame["best_effort_timestamp_time"]) for frame in frames
                 if frame.get("media_type") == kind and "best_effort_timestamp_time" in frame]
        assert len(times) >= 2 and all(math.isfinite(value) for value in times), f"Missing decoded {kind} frames"
        span = max(times) - min(times)
        assert span >= 0.25, f"Insufficient decoded {kind} duration: {span}"
        result[kind] = {"frames": len(times), "span_seconds": span}
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifact-dir", type=Path, default=ROOT / "artifacts/quality/streaming-implementation/real-api")
    parser.add_argument("--url", action="append", help="Authorized public YouTube/Vimeo source; repeatable")
    parser.add_argument("--playlist-url", help="Public provider playlist to verify real flat extraction")
    args = parser.parse_args()
    urls = args.url or ["https://www.youtube.com/watch?v=aqz-KE-bpKQ", "https://vimeo.com/1084537"]
    target = args.artifact_dir.resolve()
    target.mkdir(parents=True, exist_ok=True)
    profile = target / "data"
    profile.mkdir(exist_ok=True)
    config = {"theme": "dark", "default_format": "video", "cookie_source": "none",
              "cookie_consent": False, "sponsorblock_consent": False,
              "auto_update_engine": True, "auto_update_app": False, "notifications": False}
    (profile / "config.json").write_text(json.dumps(config), encoding="utf-8")
    with socket.socket() as reservation:
        reservation.bind(("127.0.0.1", 0))
        port = reservation.getsockname()[1]
    token = uuid4().hex
    environment = {**os.environ, "DR_DOWNLOAD_DATA_DIR": str(profile), "DR_DOWNLOAD_PORT": str(port),
                   "DR_DOWNLOAD_TOKEN": token, "DR_DOWNLOAD_NODE": str(ROOT / "electron/resources/node/node.exe"),
                   "DR_DOWNLOAD_FFMPEG": str(ROOT / "electron/resources/ffmpeg")}
    evidence = {"started_at_utc": datetime.now(timezone.utc).isoformat(),
                "commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
                "dirty": bool(subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT, text=True)),
                "os": platform.platform(), "command": sys.argv,
                "scope": "Real source backend, bundled engine/FFmpeg, provider network, isolated SQLite; no installed GUI acceptance",
                "status": "failed", "videos": [], "checks": [], "publishable": False}
    process = None
    sessions = []
    try:
        with (target / "backend.log").open("w", encoding="utf-8") as output:
            process = subprocess.Popen([sys.executable, "-m", "backend.main"], cwd=ROOT, env=environment,
                                       stdout=output, stderr=subprocess.STDOUT,
                                       creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
        with httpx.Client(base_url=f"http://127.0.0.1:{port}", headers={"X-Dr-Download-Token": token}, timeout=100) as client:
            deadline = time.monotonic() + 125
            while True:
                if process.poll() is not None:
                    raise RuntimeError("Backend exited during startup; inspect backend.log")
                try:
                    if client.get("/health", timeout=2).status_code == 200:
                        break
                except httpx.HTTPError:
                    pass
                if time.monotonic() >= deadline:
                    raise TimeoutError("Backend startup exceeded 125 s")
                time.sleep(0.25)
            for url in urls:
                started = time.monotonic()
                response = client.post("/playback", json={"url": url, "cookie_source": "none", "max_height": 1080})
                item = {"source": url, "resolution_seconds": time.monotonic() - started, "status": response.status_code,
                        "metadata": response.json()}
                evidence["videos"].append(item)
                assert response.status_code == 200, item
                session = response.json()["session_id"]
                sessions.append(session)
                samples = []
                item["samples"] = samples
                for revision, start in enumerate((0, 15.23)):
                    stream_start = time.monotonic()
                    sample = bytearray()
                    first_byte = None
                    with client.stream("GET", f"/playback/{session}/stream", params={"start": start, "revision": revision}) as stream:
                        assert stream.status_code == 200, stream.read().decode(errors="replace")
                        assert stream.headers.get("cache-control") == "no-store"
                        for chunk in stream.iter_bytes():
                            if first_byte is None:
                                first_byte = time.monotonic() - stream_start
                            sample.extend(chunk)
                            # Include audio after the video keyframe lead-in and a complete MP4 fragment.
                            if len(sample) >= 8 * 1024 * 1024:
                                break
                    elapsed = time.monotonic() - stream_start
                    probe = subprocess.run([environment["DR_DOWNLOAD_FFMPEG"] + "/ffprobe.exe", "-v", "error", "-show_frames", "-show_entries",
                                            "stream=codec_type,codec_name,width,height:frame=media_type,best_effort_timestamp_time", "-of", "json", "pipe:0"],
                                           input=sample, capture_output=True, check=False, timeout=20)
                    metadata = client.get(f"/playback/{session}").json()
                    samples.append({"requested_start": start, "first_byte_seconds": first_byte,
                                    "receive_seconds": elapsed, "bytes": len(sample), "probe_code": probe.returncode,
                                    "sha256": hashlib.sha256(sample).hexdigest(), "session": metadata})
                    assert probe.returncode == 0, samples[-1]
                    assert metadata.get("error") is None, samples[-1]
                    details = json.loads(probe.stdout)
                    assert {track["codec_type"] for track in details["streams"]} == {"video", "audio"}, details
                    samples[-1]["streams"] = details["streams"]
                    samples[-1]["decoded"] = decoded_track_summary(details.get("frames", []))
                with client.stream("GET", f"/playback/{session}/stream", params={"start": 0, "revision": 0}) as stale:
                    assert stale.status_code == 409, "An older browser retry replaced the newer stream"
                    assert json.loads(stale.read())["detail"]["code"] == "playback_cancelled"
                evidence["checks"].append({"name": "older stream revision rejected over real HTTP", "passed": True, "source": url})
                assert client.delete(f"/playback/{session}").status_code == 204
            playlist = client.post("/playlists", json={"name": "Real smoke " + uuid4().hex[:8]}).json()
            for url in urls:
                result = client.post(f"/playlists/{playlist['id']}/items", json={"url": url})
                assert result.status_code == 200, result.text
            persisted = client.get("/playlists").json()
            assert any(value["id"] == playlist["id"] and len(value["items"]) == len(set(urls)) for value in persisted)
            evidence["checks"].append({"name": "playlist CRUD real SQLite", "passed": True, "playlist_id": playlist["id"]})
            if args.playlist_url:
                imported = client.post("/playlists/import", json={"request_id": str(uuid4()), "url": args.playlist_url, "cookie_source": "none"})
                evidence["import"] = {"status": imported.status_code, "result": imported.json()}
                assert imported.status_code == 200, imported.text
            client.post("/shutdown/").raise_for_status()
        evidence["status"] = "passed"
    except Exception as error:
        evidence["failure"] = str(error)
    finally:
        if process:
            if process.poll() is None:
                try:
                    httpx.post(f"http://127.0.0.1:{port}/shutdown/", headers={"X-Dr-Download-Token": token}, timeout=20)
                except httpx.HTTPError:
                    pass
                process.terminate()
            process.wait(timeout=20)
        evidence["finished_at_utc"] = datetime.now(timezone.utc).isoformat()
        hashes = {}
        for filename in subprocess.check_output(["git", "ls-files", "--cached", "--others", "--exclude-standard", "backend", "electron", "tools", "docs"], cwd=ROOT, text=True).splitlines():
            file = ROOT / filename
            if file.is_file():
                hashes[filename] = hashlib.sha256(file.read_bytes()).hexdigest()
        for file in (ROOT / "backend").glob("play*.py"):
            hashes[file.relative_to(ROOT).as_posix()] = hashlib.sha256(file.read_bytes()).hexdigest()
        evidence["source_sha256"] = hashlib.sha256(json.dumps(hashes, sort_keys=True).encode()).hexdigest()
        (target / "evidence.json").write_text(json.dumps(evidence, indent=2, ensure_ascii=False), encoding="utf-8")
        print(json.dumps({key: evidence.get(key) for key in ("status", "failure", "source_sha256")}, ensure_ascii=False))
    return 0 if evidence["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
