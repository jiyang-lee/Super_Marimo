from types import SimpleNamespace
import time

from bridge.core.vad_profile import build_vad_profile
from bridge.main import Bridge


def test_build_vad_profile_uses_boosted_reply_settings() -> None:
    args = SimpleNamespace(
        start_rms=900,
        stop_rms=500,
        start_frames=2,
        silence_frames=8,
        min_segment_sec=0.3,
        wake_min_segment_sec=0.3,
        reply_start_rms=650,
        reply_stop_rms=325,
        reply_start_frames=1,
        reply_silence_frames=14,
        reply_min_segment_sec=0.35,
    )

    normal = build_vad_profile(args, boosted=False)
    boosted = build_vad_profile(args, boosted=True)

    assert normal.start_rms == 900
    assert normal.stop_rms == 500
    assert normal.start_frames == 2
    assert normal.silence_frames == 8
    assert normal.min_segment_sec == 0.3

    assert boosted.start_rms == 650
    assert boosted.stop_rms == 325
    assert boosted.start_frames == 1
    assert boosted.silence_frames == 14
    assert boosted.min_segment_sec == 0.35


def test_reply_window_counts_as_active_conversation() -> None:
    bridge = Bridge.__new__(Bridge)
    bridge.armed_until = 0.0
    bridge.distance_followup_until = 0.0
    bridge.reply_window_until = 0.0

    assert bridge.is_conversation_active() is False

    bridge.reply_window_until = time.time() + 1000
    assert bridge.is_conversation_active() is True
