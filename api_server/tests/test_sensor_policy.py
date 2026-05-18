from types import SimpleNamespace

from services.sensor_judge import judge_realtime_state
from services.sensor_policy import build_realtime_next_action


class _DummyConn:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


def test_judge_realtime_state_uses_distance_threshold(monkeypatch) -> None:
    monkeypatch.setattr("services.sensor_service.SENSOR_WARNING_DISTANCE_THRESHOLD_CM", 12.0)

    state = judge_realtime_state(SimpleNamespace(light=500.0, distance=11.5))

    assert state["level"] == "warning"
    assert "물체가 가까움" in state["alerts"]


def test_build_realtime_next_action_returns_proactive_greeting(monkeypatch) -> None:
    saved_events: list[dict[str, object]] = []

    def fake_save_device_event(payload: dict[str, object]) -> dict[str, object]:
        saved_events.append(payload)
        return {
            "saved": True,
            "event": {
                "event_id": len(saved_events),
                "event_type": payload["event_type"],
            },
        }

    monkeypatch.setattr("services.sensor_service.save_device_event", fake_save_device_event)
    monkeypatch.setattr("services.sensor_service.get_db_connection", lambda: _DummyConn())
    monkeypatch.setattr(
        "services.sensor_service.can_emit_proactive_greeting",
        lambda conn: {"allowed": True, "last_greeting_at": None, "cooldown_remaining_sec": 0},
    )
    monkeypatch.setattr("services.sensor_service.PROACTIVE_GREETING_TEXT", "테스트 인사")
    monkeypatch.setattr("services.sensor_service.SENSOR_WARNING_DISTANCE_THRESHOLD_CM", 10.0)

    payload = SimpleNamespace(
        light=500.0,
        distance=8.0,
        model_dump=lambda: {"distance": 8.0, "light": 500.0},
    )
    result = build_realtime_next_action(
        payload,
        session_id="11111111-1111-1111-1111-111111111111",
        device_id="rp2040-01",
        trigger_source="sensor",
    )

    assert result["type"] == "proactive_greeting"
    assert result["text"] == "테스트 인사"
    assert result["warning_event"]["event_type"] == "sensor_warning"
    assert result["device_event"]["event_type"] == "proactive_greeting"
    assert [event["event_type"] for event in saved_events] == ["sensor_warning", "proactive_greeting"]


def test_build_realtime_next_action_skips_greeting_during_cooldown(monkeypatch) -> None:
    saved_events: list[dict[str, object]] = []

    def fake_save_device_event(payload: dict[str, object]) -> dict[str, object]:
        saved_events.append(payload)
        return {
            "saved": True,
            "event": {
                "event_id": len(saved_events),
                "event_type": payload["event_type"],
            },
        }

    monkeypatch.setattr("services.sensor_service.save_device_event", fake_save_device_event)
    monkeypatch.setattr("services.sensor_service.get_db_connection", lambda: _DummyConn())
    monkeypatch.setattr(
        "services.sensor_service.can_emit_proactive_greeting",
        lambda conn: {"allowed": False, "last_greeting_at": "2026-05-18T12:00:00+09:00", "cooldown_remaining_sec": 120},
    )
    monkeypatch.setattr("services.sensor_service.SENSOR_WARNING_DISTANCE_THRESHOLD_CM", 10.0)

    payload = SimpleNamespace(
        light=500.0,
        distance=8.0,
        model_dump=lambda: {"distance": 8.0, "light": 500.0},
    )
    result = build_realtime_next_action(
        payload,
        session_id="11111111-1111-1111-1111-111111111111",
        device_id="rp2040-01",
        trigger_source="sensor",
    )

    assert result["type"] == "sensor_warning"
    assert result["cooldown_remaining_sec"] == 120
    assert [event["event_type"] for event in saved_events] == ["sensor_warning"]
