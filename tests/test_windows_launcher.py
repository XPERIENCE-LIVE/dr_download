import json
import socket
import subprocess
import sys
from pathlib import Path

import pytest


pytestmark = pytest.mark.skipif(
    sys.platform != "win32", reason="Windows launcher test"
)


def test_electron_start_uses_node_instead_of_shadowed_electron_command():
    root = Path(__file__).resolve().parents[1]
    package = json.loads((root / "electron" / "package.json").read_text())

    assert package["scripts"]["start"] == "node node_modules/electron/cli.js ."


def test_requirements_do_not_embed_a_second_youtube_engine():
    root = Path(__file__).resolve().parents[1]
    requirements = (root / "backend" / "requirements.txt").read_text()
    updater = (root / "backend" / "engine_updater.py").read_text()

    assert "yt-dlp" not in requirements
    assert "https://github.com/yt-dlp/yt-dlp/releases/latest/download" in updater
    assert 'parse_sha256(response.read().decode("utf-8"), "yt-dlp.exe")' in updater


def test_launcher_leaves_backend_lifecycle_to_electron():
    root = Path(__file__).resolve().parents[1]
    launcher = (
        root / "electron" / "run_progressia_downloader.ps1"
    ).read_text()

    assert "Start-Process" not in launcher
    assert "127.0.0.1:8000" not in launcher
    assert 'Invoke-NativeCommand "npm.cmd" @("start")' in launcher


def test_windows_launcher_check_mode_validates_without_leaving_backend_running():
    root = Path(__file__).resolve().parents[1]
    script = root / "electron" / "run_progressia_downloader.ps1"

    result = subprocess.run(
        [
            "powershell.exe",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(script),
            "-CheckOnly",
        ],
        cwd=root,
        capture_output=True,
        text=True,
        timeout=120,
    )

    output = result.stdout + result.stderr
    assert result.returncode == 0, output
    assert "LAUNCHER_CHECK_OK" in output

    with pytest.raises(OSError):
        socket.create_connection(("127.0.0.1", 8000), timeout=0.5)
