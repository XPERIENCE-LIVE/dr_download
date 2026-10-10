import hashlib
from unittest.mock import patch

import pytest

from backend.engine_updater import ensure_engine_ready, install_verified, parse_sha256, update_if_due
from backend.engine_updater import start_background_update


def test_parse_sha256_finds_exact_windows_asset():
    digest = "a" * 64
    sums = f"{digest}  yt-dlp.exe\n{'b' * 64}  yt-dlp_linux\n"
    assert parse_sha256(sums, "yt-dlp.exe") == digest


def test_install_verified_promotes_binary_and_keeps_previous(tmp_path):
    target = tmp_path / "yt-dlp.exe"
    target.write_bytes(b"old")
    candidate = tmp_path / "candidate.exe"
    candidate.write_bytes(b"new")
    digest = hashlib.sha256(b"new").hexdigest()

    install_verified(candidate, target, digest, health_check=lambda path: path.read_bytes() == b"new")

    assert target.read_bytes() == b"new"
    assert target.with_suffix(".exe.previous").read_bytes() == b"old"


def test_install_verified_rejects_checksum_and_preserves_current(tmp_path):
    target = tmp_path / "yt-dlp.exe"
    target.write_bytes(b"old")
    candidate = tmp_path / "candidate.exe"
    candidate.write_bytes(b"tampered")

    with pytest.raises(ValueError, match="checksum"):
        install_verified(candidate, target, "0" * 64)
    assert target.read_bytes() == b"old"


def test_background_update_does_not_start_when_disabled():
    assert start_background_update(".", enabled=False) is None


def test_failed_update_is_not_retried_again_within_interval(tmp_path):
    with patch("backend.engine_updater.urllib.request.urlopen", side_effect=OSError("offline")) as open_url:
        assert update_if_due(tmp_path) is None
        assert update_if_due(tmp_path) is None

    assert open_url.call_count == 1
    assert (tmp_path / "engine" / "last-check").exists()


def test_first_start_fails_closed_when_verified_engine_cannot_be_installed(tmp_path):
    with patch("backend.engine_updater.update_if_due", return_value=None):
        with pytest.raises(RuntimeError, match="yt-dlp engine is unavailable"):
            ensure_engine_ready(tmp_path, updates_enabled=True)


def test_existing_healthy_engine_is_ready_without_network(tmp_path):
    engine = tmp_path / "engine" / "yt-dlp.exe"
    engine.parent.mkdir()
    engine.write_bytes(b"engine")

    with patch("backend.engine_updater._healthy", return_value=True), patch(
        "backend.engine_updater.start_background_update"
    ) as background:
        assert ensure_engine_ready(tmp_path, updates_enabled=True) == engine

    background.assert_called_once_with(tmp_path, True)
