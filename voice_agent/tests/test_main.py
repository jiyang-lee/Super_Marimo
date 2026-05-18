from importlib import util
from pathlib import Path

from fastapi.testclient import TestClient


VOICE_MAIN_PATH = Path(__file__).resolve().parents[1] / "main.py"
spec = util.spec_from_file_location("voice_agent_main", VOICE_MAIN_PATH)
assert spec is not None and spec.loader is not None
voice_main = util.module_from_spec(spec)
spec.loader.exec_module(voice_main)
voice_main.AskPayload.model_rebuild(_types_namespace=vars(voice_main))
voice_main.AskResponse.model_rebuild(_types_namespace=vars(voice_main))


def test_health_reports_api_and_downstream(monkeypatch) -> None:
    monkeypatch.setattr(voice_main, "load_session_id", lambda: "session-123")
    monkeypatch.setattr(voice_main, "api_health", lambda: {"ok": True, "data": {"ok": True}})
    monkeypatch.setattr(voice_main, "voice_health", lambda: {"ok": True, "data": {"ok": True}})
    monkeypatch.setattr(voice_main, "llm_health", lambda: {"ok": True, "data": {"ok": True}})

    client = TestClient(voice_main.app)
    response = client.get("/health")

    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    assert payload["server"] == "voice-agent"
    assert payload["session_id"] == "session-123"
    assert payload["api_server"]["ok"] is True
    assert payload["voice_server"]["ok"] is True
    assert payload["llm_server"]["ok"] is True


def test_ask_routes_through_api_server(monkeypatch) -> None:
    saved_sessions: list[str] = []

    monkeypatch.setattr(voice_main, "load_session_id", lambda: None)
    monkeypatch.setattr(voice_main, "save_session_id", lambda session_id: saved_sessions.append(session_id))
    monkeypatch.setattr(voice_main, "api_health", lambda: {"ok": True, "data": {"ok": True}})
    monkeypatch.setattr(voice_main, "voice_health", lambda: {"ok": True, "data": {"ok": True}})
    monkeypatch.setattr(voice_main, "llm_health", lambda: {"ok": True, "data": {"ok": True}})
    monkeypatch.setattr(
        voice_main,
        "ask_api_server",
        lambda text, session_id: {
            "saved": True,
            "session_id": session_id,
            "interaction_id": 7,
            "session_created": True,
            "messages_saved": 2,
            "tts_text": f"응답: {text}",
        },
    )
    monkeypatch.setattr(voice_main, "synthesize_tts", lambda text: f"C:/temp/{text}.wav")

    client = TestClient(voice_main.app)
    response = client.post(
        "/ask",
        json={
            "text": "테스트 질문",
            "session_id": "11111111-1111-1111-1111-111111111111",
            "speak": True,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["saved"] is True
    assert payload["answer"] == "응답: 테스트 질문"
    assert payload["session_id"] == "11111111-1111-1111-1111-111111111111"
    assert payload["tts_ok"] is True
    assert payload["interaction_id"] == 7
    assert payload["messages_saved"] == 2
    assert payload["session_created"] is True
    assert saved_sessions[-1] == "11111111-1111-1111-1111-111111111111"
