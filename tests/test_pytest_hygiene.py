"""Pytest scratch output stays in build/, never as clutter in the repository root."""
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_temporary_paths_live_under_build(tmp_path):
    assert tmp_path.resolve().is_relative_to((ROOT / "build" / "pytest-tmp").resolve())


def test_cache_lives_under_build(pytestconfig):
    assert pytestconfig.getini("cache_dir") == "build/pytest-cache"


def test_basetemp_inside_repository_but_outside_build_is_rejected():
    # A relative --basetemp resolves against the invocation folder, here backend/.
    probe = ROOT / "backend" / ".pytest-probe"
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pytest", "--basetemp=.pytest-probe", "--collect-only", "-q", __file__],
            cwd=ROOT / "backend", capture_output=True, text=True, timeout=120,
        )
        assert result.returncode == 4, result.stdout + result.stderr
        assert "build/pytest-tmp" in result.stdout + result.stderr
        assert not probe.exists()
    finally:
        shutil.rmtree(probe, ignore_errors=True)
