from backend import config


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

    # Save partial config and reload
    partial = {"theme": "light"}
    config.save_config(partial)
    cfg_loaded = config.load_config()
    # Missing keys should be filled with defaults
    assert cfg_loaded["default_format"] == config.DEFAULT_CONFIG["default_format"]
    assert cfg_loaded["log_max_bytes"] == config.DEFAULT_CONFIG["log_max_bytes"]
    assert cfg_loaded["log_backup_count"] == config.DEFAULT_CONFIG["log_backup_count"]
