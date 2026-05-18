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

    assert prototype.pick_wake_greeting() == "\uc548\ub155? \uc9c0\uae08 \ubb50\ud574?"


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
