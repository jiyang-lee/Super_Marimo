import json

from bridge.core.api_bridge import ApiBridge


def test_api_bridge_ignores_ended_session_file(tmp_path, monkeypatch) -> None:
    session_file = tmp_path / "session.json"
    session_file.write_text(json.dumps({"session_id": "11111111-1111-1111-1111-111111111111"}), encoding="utf-8")

    def fake_get_json(url: str, timeout: int):  # noqa: ANN001
        return {"session": {"ended_at": "2026-05-21T00:00:00Z"}}

    monkeypatch.setattr("bridge.core.api_bridge._get_json", fake_get_json)

    bridge = ApiBridge("http://voice-agent", "http://api-server", session_file)

    assert bridge.active_session_id is None
    assert not session_file.exists()


def test_api_bridge_keeps_active_session_file(tmp_path, monkeypatch) -> None:
    session_file = tmp_path / "session.json"
    session_file.write_text(json.dumps({"session_id": "11111111-1111-1111-1111-111111111111"}), encoding="utf-8")

    def fake_get_json(url: str, timeout: int):  # noqa: ANN001
        return {"session": {"ended_at": None}}

    monkeypatch.setattr("bridge.core.api_bridge._get_json", fake_get_json)

    bridge = ApiBridge("http://voice-agent", "http://api-server", session_file)

    assert bridge.active_session_id == "11111111-1111-1111-1111-111111111111"
    assert session_file.exists()
