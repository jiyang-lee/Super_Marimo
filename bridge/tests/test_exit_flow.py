from types import SimpleNamespace
import time

from bridge.main import Bridge


def test_exit_tts_does_not_open_reply_window_when_suppressed() -> None:
    bridge = Bridge.__new__(Bridge)
    bridge.args = type("Args", (), {"reply_boost_sec": 12, "distance_followup_timeout_sec": 30})()
    bridge.distance_followup_until = 0.0
    bridge.reply_window_until = 0.0
    bridge.suppress_next_reply_boost = True

    bridge._on_audio_played("ask_123.wav")

    assert bridge.suppress_next_reply_boost is False
    assert bridge.reply_window_until == 0.0


def test_normal_tts_still_opens_reply_window() -> None:
    bridge = Bridge.__new__(Bridge)
    bridge.args = type("Args", (), {"reply_boost_sec": 12, "distance_followup_timeout_sec": 30})()
    bridge.distance_followup_until = 0.0
    bridge.reply_window_until = 0.0
    bridge.suppress_next_reply_boost = False

    bridge._on_audio_played("ask_123.wav")

    assert bridge.reply_window_until > 0.0


def test_exit_phrase_ends_session_without_llm_tts(monkeypatch) -> None:
    calls = {"ask": 0, "end": 0}

    class _FakeApiBridge:
        active_session_id = "session-1"

        def ask(self, *args, **kwargs):
            calls["ask"] += 1
            raise AssertionError("ask should not be called for exit phrase")

        def end_session(self):
            calls["end"] += 1

    class _FakeSttClient:
        def transcribe(self, wav_bytes):
            return "잘가 마리모"

    class _FakeLogger:
        def log(self, *args, **kwargs):
            return None

    bridge = Bridge.__new__(Bridge)
    bridge.args = SimpleNamespace(
        min_segment_sec=0.01,
        reply_min_segment_sec=0.01,
        wake_timeout_sec=12,
    )
    bridge.api_bridge = _FakeApiBridge()
    bridge.stt_client = _FakeSttClient()
    bridge.event_logger = _FakeLogger()
    bridge.armed_until = 0.0
    bridge.distance_followup_until = 0.0
    bridge.reply_window_until = 0.0
    bridge.suppress_next_reply_boost = False
    bridge.transcript_buffer = ""
    bridge.is_reply_boost_active = lambda: False
    bridge._handle_wake = lambda transcript: (_ for _ in ()).throw(AssertionError("wake path should not run"))
    bridge._handle_distance_followup = lambda transcript: (_ for _ in ()).throw(AssertionError("follow-up path should not run"))

    pcm_bytes = b"\x00\x00" * 400
    bridge.handle_segment(pcm_bytes)

    assert calls["ask"] == 0
    assert calls["end"] == 1


def test_reply_window_triggers_answer_turn_without_wake(monkeypatch) -> None:
    calls = {"answer": 0}

    class _FakeApiBridge:
        active_session_id = "session-1"

        def ask(self, *args, **kwargs):
            return {"answer": "괜찮아", "session_id": "session-1", "interaction_id": 1, "messages_saved": 1}

    class _FakeSttClient:
        def transcribe(self, wav_bytes):
            return "오늘 상태 어때"

    class _FakeLogger:
        def log(self, *args, **kwargs):
            return None

    bridge = Bridge.__new__(Bridge)
    bridge.args = SimpleNamespace(
        min_segment_sec=0.01,
        reply_min_segment_sec=0.01,
        wake_min_segment_sec=0.01,
        wake_timeout_sec=12,
        reply_boost_sec=12,
    )
    bridge.api_bridge = _FakeApiBridge()
    bridge.stt_client = _FakeSttClient()
    bridge.event_logger = _FakeLogger()
    bridge.armed_until = 0.0
    bridge.distance_followup_until = 0.0
    bridge.reply_window_until = time.time() + 10
    bridge.suppress_next_reply_boost = False
    bridge.transcript_buffer = ""
    bridge.is_reply_boost_active = lambda: True
    bridge._handle_wake = lambda transcript: (_ for _ in ()).throw(AssertionError("wake path should not run"))
    bridge._handle_distance_followup = lambda transcript: (_ for _ in ()).throw(AssertionError("follow-up path should not run"))

    def _answer_turn(text: str) -> None:
        calls["answer"] += 1

    bridge.answer_turn = _answer_turn

    pcm_bytes = b"\x00\x00" * 400
    bridge.handle_segment(pcm_bytes)

    assert calls["answer"] == 1


def test_tts_mute_skips_segments_during_playback(monkeypatch) -> None:
    calls = {"stt": 0}

    class _FakeApiBridge:
        active_session_id = "session-1"

    class _FakeSttClient:
        def transcribe(self, wav_bytes):
            calls["stt"] += 1
            return "안녕"

    class _FakeLogger:
        def log(self, *args, **kwargs):
            return None

    bridge = Bridge.__new__(Bridge)
    bridge.args = SimpleNamespace(
        min_segment_sec=0.01,
        reply_min_segment_sec=0.01,
        wake_min_segment_sec=0.01,
        wake_timeout_sec=12,
        reply_boost_sec=12,
    )
    bridge.api_bridge = _FakeApiBridge()
    bridge.stt_client = _FakeSttClient()
    bridge.event_logger = _FakeLogger()
    bridge.armed_until = 0.0
    bridge.distance_followup_until = 0.0
    bridge.reply_window_until = 0.0
    bridge.tts_mute_until = time.time() + 10
    bridge.suppress_next_reply_boost = False
    bridge.transcript_buffer = ""
    bridge.is_reply_boost_active = lambda: False

    pcm_bytes = b"\x00\x00" * 400
    bridge.handle_segment(pcm_bytes)

    assert calls["stt"] == 0


def test_audio_playing_sets_tts_mute_window() -> None:
    bridge = Bridge.__new__(Bridge)
    bridge.tts_mute_until = 0.0

    bridge._on_audio_playing("ask_123.wav")

    assert bridge.tts_mute_until > time.time()
