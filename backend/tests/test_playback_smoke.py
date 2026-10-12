import pytest

from tools.smoke_test_playback import decoded_track_summary


def test_decoded_track_summary_requires_both_tracks_and_elapsed_media():
    frames = [{"media_type": kind, "best_effort_timestamp_time": stamp}
              for kind in ("video", "audio") for stamp in ("0", "0.5")]
    assert decoded_track_summary(frames) == {
        "video": {"frames": 2, "span_seconds": 0.5},
        "audio": {"frames": 2, "span_seconds": 0.5},
    }


@pytest.mark.parametrize("frames", [[],
    [{"media_type": "video", "best_effort_timestamp_time": str(n / 25)} for n in range(3)],
    [{"media_type": kind, "best_effort_timestamp_time": stamp}
     for kind in ("video", "audio") for stamp in ("0", "nan")],
    [{"media_type": kind, "best_effort_timestamp_time": "0"}
     for kind in ("video", "audio") for _ in range(2)],
])
def test_decoded_track_summary_rejects_headers_missing_audio_and_invalid_time(frames):
    with pytest.raises(AssertionError):
        decoded_track_summary(frames)
