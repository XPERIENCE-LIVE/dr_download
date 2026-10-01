import pytest

from backend.error_mapping import classify_error


@pytest.mark.parametrize(
    ("message", "cookie_source", "code"),
    [
        ("Failed to decrypt with DPAPI", "edge", "session_required"),
        ("Could not copy Chrome cookie database", "edge", "browser_locked"),
        ("Permission denied: cookies.sqlite", "firefox", "browser_locked"),
        ("No space left on device", "none", "disk_full"),
        ("Requested format is not available", "none", "format_unavailable"),
        ("FFmpeg is unavailable", "none", "ffmpeg_missing"),
        ("network timeout while reading", "none", "network_error"),
        ("extractor exploded", "none", "engine_error"),
    ],
)
def test_classify_error_returns_safe_actionable_codes(message, cookie_source, code):
    result = classify_error(message, cookie_source)

    assert result["code"] == code
    assert result["message"]
    assert result["recovery"]
    assert message not in result.values()


@pytest.mark.parametrize("cookie_source", ["none", "edge", "firefox"])
def test_age_restriction_explains_required_account_instead_of_engine_update(cookie_source):
    result = classify_error(
        "ERROR: [youtube] _5YRkb6FEGY: Sign in to confirm your age. "
        "Use --cookies-from-browser or --cookies for the authentication.",
        cookie_source,
    )
    assert result["code"] == "age_restricted"
    assert "edad" in result["message"]
    assert "Actualiza" not in result["recovery"]
    if cookie_source == "none":
        assert "Ajustes" in result["recovery"] and "cookies" in result["recovery"]
    else:
        browser = "Edge" if cookie_source == "edge" else "Firefox"
        assert browser in result["recovery"]
        assert "cuenta" in result["recovery"]
