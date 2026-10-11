"""Pytest scratch output stays in build/, never as clutter in the repository root."""
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def test_temporary_paths_live_under_build(tmp_path):
    assert tmp_path.resolve().is_relative_to((ROOT / "build" / "pytest-tmp").resolve())


def test_cache_lives_under_build(pytestconfig):
    assert pytestconfig.getini("cache_dir") == "build/pytest-cache"


@pytest.mark.parametrize("arguments", [[], ["--basetemp=build/nested/scratch"]])
def test_fresh_checkout_creates_scratch_parent_before_tmp_path(tmp_path, arguments):
    checkout = tmp_path / "checkout"
    checkout.mkdir()
    shutil.copyfile(ROOT / "conftest.py", checkout / "conftest.py")
    (checkout / "pytest.ini").write_text("[pytest]\ncache_dir = build/pytest-cache\n", encoding="utf-8")
    (checkout / "test_probe.py").write_text(
        "def test_scratch(tmp_path):\n    (tmp_path / 'probe').write_text('real filesystem')\n",
        encoding="utf-8",
    )
    assert not (checkout / "build").exists()
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", *arguments], cwd=checkout,
        capture_output=True, text=True, timeout=120,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert list((checkout / "build").rglob("probe"))


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
