from importlib import util
from pathlib import Path


VOICE_PROTO_PATH = Path(__file__).resolve().parents[1] / "serial_voice_proto.py"
spec = util.spec_from_file_location("serial_voice_proto", VOICE_PROTO_PATH)
assert spec is not None and spec.loader is not None
serial_voice_proto = util.module_from_spec(spec)
spec.loader.exec_module(serial_voice_proto)


def _build_args(session_state_file: str):
    return serial_voice_proto.argparse.Namespace(
        debug_dir="arduino\\captures",
        session_state_file=session_state_file,
        stt_endpoint="http://127.0.0.1:8002/stt",
        stt_model="fast",
        tts_endpoint="http://127.0.0.1:8002/tts",
        api_endpoint="http://127.0.0.1:8000/voice/ask",
        events_endpoint="http://127.0.0.1:8000/events",
        port="COM4",
        baudrate=921600,
        history_turns=6,
        wake_timeout_sec=120,
        start_rms=900,
        stop_rms=500,
        start_frames=2,
        silence_frames=10,
        max_segment_sec=8.0,
        min_segment_sec=0.7,
        pre_roll_frames=8,
    )


def test_pick_wake_greeting_uses_random_choice(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(serial_voice_proto.random, "choice", lambda items: items[1])

    prototype = serial_voice_proto.VoicePrototype(_build_args(str(tmp_path / "voice_session.json")))

    assert prototype.pick_wake_greeting() == "응, 마리모야. 편하게 이야기해도 돼."


def test_has_wake_phrase_accepts_common_misheard_variants() -> None:
    assert serial_voice_proto.has_wake_phrase("안녕 마리모")
    assert serial_voice_proto.has_wake_phrase("마린모야")
    assert not serial_voice_proto.has_wake_phrase("마리모는 누구야?")
    assert not serial_voice_proto.has_wake_phrase("아니 마리모가 누구냐고")


def test_noise_transcript_detects_laughing_segments() -> None:
    assert serial_voice_proto.is_noise_transcript("ㅋㅋㅋㅋㅋㅋ")
    assert serial_voice_proto.is_noise_transcript("")
    assert serial_voice_proto.is_noise_transcript("음음음")
    assert not serial_voice_proto.is_noise_transcript("아 피곤해")


def test_followup_retry_keeps_real_short_statements_for_llm() -> None:
    assert serial_voice_proto.should_retry_followup("ㅋㅋㅋㅋ")
    assert serial_voice_proto.should_retry_followup("")
    assert serial_voice_proto.should_retry_followup("음음음")
    assert not serial_voice_proto.should_retry_followup("아 피곤해")
    assert not serial_voice_proto.should_retry_followup("아 진짜 피곤하다")
    assert not serial_voice_proto.should_retry_followup("좀 피곤해")
    assert not serial_voice_proto.should_retry_followup("너 지금 뭐해?")


def test_sanitize_tts_text_removes_variation_selectors() -> None:
    assert serial_voice_proto.sanitize_tts_text("저녁 메뉴 고민되시나요? 어떤 음식 좋아하세요? ️") == "저녁 메뉴 고민되시나요? 어떤 음식 좋아하세요?"


def test_sanitize_tts_text_removes_parenthetical_english() -> None:
    text = "(Marimo)는 원형의 녹색 또는 흰색 덩어리 형태를 가진 생물입니다."

    assert serial_voice_proto.sanitize_tts_text(text) == "원형의 녹색 또는 흰색 덩어리 형태를 가진 생물입니다."


def test_exit_phrase_is_broad() -> None:
    assert serial_voice_proto.has_exit_phrase("잘가")
    assert serial_voice_proto.has_exit_phrase("잘 가")
    assert serial_voice_proto.has_exit_phrase("바이")
    assert serial_voice_proto.has_exit_phrase("대화 종료")
    assert serial_voice_proto.has_exit_phrase("그만해")
    assert not serial_voice_proto.has_exit_phrase("안녕")


def test_end_active_session_calls_session_endpoint(tmp_path, monkeypatch) -> None:
    calls: list[tuple[str, dict[str, object]]] = []

    def fake_post_json(url: str, payload: dict, timeout: int) -> dict:
        calls.append((url, payload))
        return {"ok": True}

    monkeypatch.setattr(serial_voice_proto, "post_json", fake_post_json)
    prototype = serial_voice_proto.VoicePrototype(_build_args(str(tmp_path / "voice_session.json")))
    prototype.active_session_id = "11111111-1111-1111-1111-111111111111"

    prototype.end_active_session()

    assert calls[0][0] == "http://127.0.0.1:8000/sessions/11111111-1111-1111-1111-111111111111/end"
    assert calls[0][1] == {"ended_by": "serial_voice_proto"}
    assert prototype.active_session_id is None


def test_ensure_active_session_touches_session_endpoint(tmp_path, monkeypatch) -> None:
    calls: list[tuple[str, dict[str, object]]] = []

    def fake_post_json(url: str, payload: dict, timeout: int) -> dict:
        calls.append((url, payload))
        return {"ok": True}

    monkeypatch.setattr(serial_voice_proto, "post_json", fake_post_json)
    prototype = serial_voice_proto.VoicePrototype(_build_args(str(tmp_path / "voice_session.json")))

    session_id = prototype.ensure_active_session()

    assert session_id == prototype.active_session_id
    assert len(calls) == 1
    assert calls[0][0] == f"http://127.0.0.1:8000/sessions/{session_id}/touch"
    assert calls[0][1] == {"touched_by": "serial_voice_proto"}
