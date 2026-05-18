from fastapi.testclient import TestClient

from main import app


class _DummyConn:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def commit(self):
        return None


def test_session_end_routes_to_service(monkeypatch) -> None:
    captured: dict[str, object] = {}

    def fake_end_session(conn, session_id, meta=None):  # noqa: ANN001
        captured["session_id"] = str(session_id)
        captured["meta"] = meta
        return {
            "session_id": session_id,
            "created_at": None,
            "last_seen_at": None,
            "ended_at": None,
            "turn_count": 0,
            "meta": meta or {},
        }

    monkeypatch.setattr("routers.sessions.end_session", fake_end_session)
    monkeypatch.setattr("routers.sessions.get_db_connection", lambda: _DummyConn())

    client = TestClient(app)
    response = client.post("/sessions/11111111-1111-1111-1111-111111111111/end")

    assert response.status_code == 200
    payload = response.json()
    assert payload["session"]["session_id"] == "11111111-1111-1111-1111-111111111111"
    assert captured["session_id"] == "11111111-1111-1111-1111-111111111111"
    assert captured["meta"] == {"ended_by": "serial_voice_proto"}


def test_session_touch_routes_to_service(monkeypatch) -> None:
    captured: dict[str, object] = {}

    def fake_ensure_session(conn, session_id):  # noqa: ANN001
        captured["session_id"] = str(session_id)
        return (
            {
                "session_id": session_id,
                "created_at": None,
                "last_seen_at": None,
                "ended_at": None,
                "turn_count": 0,
                "meta": {},
            },
            True,
        )

    monkeypatch.setattr("routers.sessions.ensure_session", fake_ensure_session)
    monkeypatch.setattr("routers.sessions.get_db_connection", lambda: _DummyConn())

    client = TestClient(app)
    response = client.post("/sessions/11111111-1111-1111-1111-111111111111/touch")

    assert response.status_code == 200
    payload = response.json()
    assert payload["created"] is True
    assert payload["session"]["session_id"] == "11111111-1111-1111-1111-111111111111"
    assert captured["session_id"] == "11111111-1111-1111-1111-111111111111"
