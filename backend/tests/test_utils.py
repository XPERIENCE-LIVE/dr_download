import logging

from backend import utils


def test_logging_uses_data_directory_and_redacts_sensitive_values(monkeypatch, tmp_path):
    monkeypatch.setenv("DR_DOWNLOAD_DATA_DIR", str(tmp_path))
    monkeypatch.setattr(
        utils,
        "load_config",
        lambda: {"log_max_bytes": 100_000, "log_backup_count": 2},
    )

    utils.setup_logging()
    logging.getLogger("diagnostic-test").error(
        "failed https://example.com/video?token=secret at C:/Users/Wilder/private/cookies.db"
    )
    for handler in logging.getLogger().handlers:
        handler.flush()

    log_file = tmp_path / "logs" / "backend.log"
    text = log_file.read_text(encoding="utf-8")
    assert "secret" not in text
    assert "Wilder" not in text
    assert "https://example.com" not in text
    assert "[URL]" in text
    assert "[PRIVATE_PATH]" in text
