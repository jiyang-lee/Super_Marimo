from importlib import util
from pathlib import Path


VOICE_MAIN_PATH = Path(__file__).resolve().parents[1] / "main.py"
spec = util.spec_from_file_location("voice_agent_main", VOICE_MAIN_PATH)
assert spec is not None and spec.loader is not None
voice_main = util.module_from_spec(spec)
spec.loader.exec_module(voice_main)
voice_main.AskPayload.model_rebuild(_types_namespace=vars(voice_main))
voice_main.AskResponse.model_rebuild(_types_namespace=vars(voice_main))


def test_health_reports_api(monkeypatch) -> None:
    monkeypatch.setattr(voice_main.session_store, "load", lambda: "session-123")
    monkeypatch.setattr(voice_main, "api_health", lambda: {"ok": True, "data": {"ok": True}})

    payload = voice_main.health()

    assert payload["ok"] is True
    assert payload["server"] == "voice-agent"
    assert payload["session_id"] == "session-123"
    assert payload["api_server"]["ok"] is True


def test_ask_routes_through_api_server(monkeypatch) -> None:
    saved_sessions: list[str] = []
    captured_api_call: dict[str, object] = {}
    captured_tts_call: dict[str, object] = {}

    monkeypatch.setattr(voice_main.session_store, "load", lambda: None)
    monkeypatch.setattr(voice_main.session_store, "save", lambda session_id: saved_sessions.append(session_id))
    monkeypatch.setattr(voice_main, "api_health", lambda: {"ok": True, "data": {"ok": True}})
    monkeypatch.setattr(
        voice_main,
        "ask_api_server",
        lambda text, session_id, persona_memo=None, system_memo=None: captured_api_call.update(
            {
                "text": text,
                "session_id": session_id,
                "persona_memo": persona_memo,
                "system_memo": system_memo,
            }
        )
        or {
            "saved": True,
            "session_id": session_id,
            "interaction_id": 7,
            "session_created": True,
            "messages_saved": 2,
            "tts_text": f"응답: {text}",
        },
    )
    monkeypatch.setattr(
        voice_main,
        "synthesize_tts",
        lambda text, voice_name=None: captured_tts_call.update({"text": text, "voice_name": voice_name})
        or f"C:/temp/{text}.wav",
    )

    payload = voice_main.AskPayload(
        text="테스트 질문",
        session_id="11111111-1111-1111-1111-111111111111",
        speak=True,
        persona_memo="다정한 말투",
        system_memo="시스템 메모",
        voice_name="F2",
    )
    response = voice_main.ask(payload)

    assert response.saved is True
    assert response.answer == "응답: 테스트 질문"
    assert response.session_id == "11111111-1111-1111-1111-111111111111"
    assert response.tts_ok is True
    assert response.interaction_id == 7
    assert response.messages_saved == 2
    assert response.session_created is True
    assert saved_sessions[-1] == "11111111-1111-1111-1111-111111111111"
    assert captured_api_call["persona_memo"] == "다정한 말투"
    assert captured_api_call["system_memo"] == "시스템 메모"
    assert captured_tts_call["voice_name"] == "F2"
