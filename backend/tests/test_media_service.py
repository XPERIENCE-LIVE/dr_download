from backend.media_service import normalize_info


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

