"""Safety checks run real PowerShell without launching an installer."""
import hashlib
import os
import re
import subprocess
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run_installer_probe(installer, digest, env):
    script = ROOT / "tools/test-installed-windows.ps1"
    assert script.exists(), "Missing real NSIS lifecycle runner"
    env.pop("PSModulePath", None)
    return subprocess.run(
        ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(script),
         "-InstallerPath", str(installer), "-ExpectedSha256", digest],
        cwd=ROOT, env=env, capture_output=True, text=True, timeout=30,
    )


def test_installer_refuses_to_modify_the_developer_machine(tmp_path):
    installer = tmp_path / "not-an-installer.exe"
    installer.write_bytes(b"never execute this")
    env = {**os.environ, "GITHUB_ACTIONS": "false", "RUNNER_ENVIRONMENT": ""}
    result = run_installer_probe(installer, hashlib.sha256(installer.read_bytes()).hexdigest(), env)
    assert result.returncode != 0
    assert "disposable GitHub-hosted Windows runner" in result.stdout + result.stderr


def test_installer_rejects_changed_candidate_before_installing(tmp_path):
    installer = tmp_path / "not-an-installer.exe"
    installer.write_bytes(b"changed artifact")
    env = {**os.environ, "GITHUB_ACTIONS": "true", "RUNNER_ENVIRONMENT": "github-hosted"}
    result = run_installer_probe(installer, "0" * 64, env)
    assert result.returncode != 0
    assert "Installer SHA-256 mismatch" in result.stdout + result.stderr


def test_signature_gate_rejects_an_unsigned_file(tmp_path):
    installer = tmp_path / "unsigned.exe"
    installer.write_bytes(b"unsigned candidate")
    env = dict(os.environ)
    env.pop("PSModulePath", None)
    result = subprocess.run(
        ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File",
         str(ROOT / "tools/validate-release.ps1"), "-InstallerPath", str(installer)],
        cwd=ROOT, env=env, capture_output=True, text=True, timeout=30,
    )
    assert result.returncode != 0
    assert "Authenticode signature is not Valid" in result.stdout + result.stderr
    assert re.sub(r"\s+", "", str(installer)) in re.sub(r"\s+", "", result.stdout + result.stderr)


def test_ffmpeg_packaging_rejects_modified_local_binaries(tmp_path):
    script = ROOT / "tools/prepare-ffmpeg.ps1"
    assert script.exists(), "Missing reproducible FFmpeg preparation"
    destination = tmp_path / "tools"
    destination.mkdir()
    shutil.copyfile(script, destination / script.name)
    resources = tmp_path / "electron/resources/ffmpeg"
    resources.mkdir(parents=True)
    for name in ("ffmpeg.exe", "ffprobe.exe", "LICENSE.txt"):
        (resources / name).write_bytes(b"not the pinned upstream binary")
    env = dict(os.environ)
    env.pop("PSModulePath", None)
    result = subprocess.run(
        ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(destination / script.name)],
        cwd=tmp_path, env=env, capture_output=True, text=True, timeout=30,
    )
    assert result.returncode != 0
    assert "FFmpeg SHA-256 mismatch" in result.stdout + result.stderr
    assert (resources / "ffmpeg.exe").read_bytes() == b"not the pinned upstream binary"
