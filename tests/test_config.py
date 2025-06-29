import sys
from pathlib import Path
import logging

backend_path = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_path))

from backend import config  # noqa: E402


def test_load_config_defaults(tmp_path, monkeypatch):
    cfg_file = tmp_path / "config.json"
    # Point config module to temporary location
    monkeypatch.setattr(config, "CONFIG_FILE", str(cfg_file))
    monkeypatch.setattr(config, "LEGACY_CONFIG", str(tmp_path / "legacy.json"))

    # Ensure fresh state
    if cfg_file.exists():
        cfg_file.unlink()

    # Loading should create file with defaults
    cfg = config.load_config()
    assert cfg["log_max_bytes"] == config.DEFAULT_CONFIG["log_max_bytes"]
    assert cfg["log_backup_count"] == config.DEFAULT_CONFIG["log_backup_count"]
    assert cfg["worker_threads"] == config.DEFAULT_CONFIG["worker_threads"]

    # Save partial config and reload
    partial = {"theme": "light"}
    config.save_config(partial)
    cfg_loaded = config.load_config()
    # Missing keys should be filled with defaults
    # fmt: off
    assert cfg_loaded["default_format"] == config.DEFAULT_CONFIG["default_format"]  # noqa: E501
    assert cfg_loaded["log_max_bytes"] == config.DEFAULT_CONFIG["log_max_bytes"]  # noqa: E501
    assert cfg_loaded["log_backup_count"] == config.DEFAULT_CONFIG["log_backup_count"]  # noqa: E501
    assert cfg_loaded["worker_threads"] == config.DEFAULT_CONFIG["worker_threads"]  # noqa: E501
    # fmt: on


def test_load_config_logs_warning_on_malformed(tmp_path, monkeypatch, caplog):
    cfg_file = tmp_path / "config.json"
    monkeypatch.setattr(config, "CONFIG_FILE", str(cfg_file))
    monkeypatch.setattr(config, "LEGACY_CONFIG", str(tmp_path / "legacy.json"))

    cfg_file.write_text("{bad json}")

    with caplog.at_level(logging.WARNING):
        cfg = config.load_config()

    assert cfg == config.DEFAULT_CONFIG
    assert any(
        "Failed to load config file" in rec.message for rec in caplog.records
    )
