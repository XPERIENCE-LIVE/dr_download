from backend.media_service import normalize_info

import pytest
from unittest.mock import patch
from backend import config
from backend.media_service import inspect_media


def test_normalize_info_exposes_audio_and_video_presets():
    result = normalize_info(
        {
            "title": "A title",
            "uploader": "A channel",
            "duration": 61,
            "thumbnail": "https://example.com/thumb.jpg",
            "formats": [
                {"format_id": "18", "vcodec": "avc1", "acodec": "mp4a", "height": 360, "ext": "mp4"},
                {"format_id": "140", "vcodec": "none", "acodec": "mp4a", "abr": 128, "ext": "m4a"},
            ],
        }
    )

    assert result["title"] == "A title"
    assert result["author"] == "A channel"
    assert result["duration"] == 61
    assert {item["kind"] for item in result["formats"]} == {"video", "audio"}
    assert any(item["id"] == "audio-mp3" for item in result["formats"])


def test_normalize_info_omits_storyboard_and_mhtml_formats():
    result = normalize_info(
        {
            "title": "A title",
            "formats": [
                {"format_id": "sb3", "vcodec": "none", "acodec": "none", "ext": "mhtml"},
                {"format_id": "storyboard", "vcodec": "images", "acodec": "none", "ext": "mhtml"},
                {"format_id": "140", "vcodec": "none", "acodec": "mp4a", "ext": "m4a"},
            ],
        }
    )

    ids = {item["id"] for item in result["formats"]}
    assert "sb3" not in ids
    assert "storyboard" not in ids
    assert "140" in ids


def test_presets_estimate_both_streams_and_keep_compatible_separate_from_best():
    result = normalize_info({"duration": 10, "formats": [
        {"format_id": "aac", "vcodec": "none", "acodec": "mp4a.40.2", "ext": "m4a", "filesize": 100},
        {"format_id": "opus", "vcodec": "none", "acodec": "opus", "ext": "webm", "filesize": 200},
        {"format_id": "h264", "vcodec": "avc1.640028", "acodec": "none", "ext": "mp4", "height": 1080, "filesize": 1000},
        {"format_id": "av1", "vcodec": "av01.0.12M.08", "acodec": "none", "ext": "mp4", "height": 2160, "filesize_approx": 2000},
    ]})
    formats = {item["id"]: item for item in result["formats"]}
    assert formats["video-compatible"]["estimated_bytes"] == 1100
    assert formats["video-best"]["estimated_bytes"] == 2100
    assert formats["h264"]["estimated_bytes"] == 1100
    assert formats["av1"]["estimated_bytes"] == 2100
    assert formats["audio-original"]["estimated_bytes"] == 200
    assert formats["audio-mp3"]["estimated_bytes"] == 240000
    assert all(formats[key]["preset"] is True for key in (
        "video-compatible", "video-best", "audio-mp3", "audio-original"
    ))


@pytest.mark.parametrize("audio", [
    {"format_id": "aac", "vcodec": "none", "acodec": "mp4a", "ext": "m4a"},
    {"format_id": "aac", "vcodec": "none", "acodec": "mp4a", "ext": "m4a", "filesize": -1},
])
def test_video_estimate_is_unknown_when_audio_size_is_unknown(audio):
    result = normalize_info({"formats": [audio, {
        "format_id": "h264", "vcodec": "avc1", "acodec": "none", "ext": "mp4", "filesize": 1000,
    }]})
    formats = {item["id"]: item for item in result["formats"]}
    assert formats["h264"]["estimated_bytes"] is None
    assert formats["video-compatible"]["estimated_bytes"] is None
    assert formats["video-best"]["estimated_bytes"] is None


def test_compatible_estimate_uses_muxed_h264_aac_and_ignores_incompatible_audio():
    result = normalize_info({"formats": [
        {"format_id": "muxed", "vcodec": "h264", "acodec": "aac", "ext": "mp4", "filesize": 500},
        {"format_id": "opus", "vcodec": "none", "acodec": "opus", "ext": "m4a", "filesize": 100},
    ]})
    formats = {item["id"]: item for item in result["formats"]}
    assert formats["video-compatible"]["estimated_bytes"] == 500
    assert formats["muxed"]["estimated_bytes"] == 500


def test_compatible_estimate_stays_unknown_without_compatible_sources():
    result = normalize_info({"formats": [
        {"format_id": "av1", "vcodec": "av01", "acodec": "opus", "ext": "webm", "filesize": 1000},
    ]})
    formats = {item["id"]: item for item in result["formats"]}
    assert formats["video-compatible"]["estimated_bytes"] is None
    assert formats["video-best"]["estimated_bytes"] == 1000


def test_inspection_service_rejects_browser_request_after_revocation(monkeypatch, tmp_path):
    monkeypatch.setattr(config, "CONFIG_FILE", str(tmp_path / "config.json"))
    config.save_config({"cookie_consent": False, "cookie_source": "edge"})
    with patch("backend.media_service.resolve_engine", return_value="yt-dlp.exe"), patch("backend.media_service.inspect_with_engine") as inspect:
        with pytest.raises(PermissionError, match="Browser consent required"):
            inspect_media("https://example.com", "edge")
    inspect.assert_not_called()

