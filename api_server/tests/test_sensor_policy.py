from types import SimpleNamespace

from services.sensor_judge import judge_hourly_state, judge_realtime_state
from services.sensor_policy import build_realtime_next_action


class _DummyConn:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


def _runtime_settings(**overrides):
    value = {
        "distance_detection_enabled": True,
        "wake_enabled": True,
        "web_voice_enabled": False,
        "distance_threshold_cm": 50.0,
        "distance_inside_threshold": False,
    }
    value.update(overrides)
    return value


def test_judge_realtime_state_uses_distance_threshold(monkeypatch) -> None:
    monkeypatch.setattr("config.SENSOR_WARNING_DISTANCE_THRESHOLD_CM", 12.0)

    state = judge_realtime_state(SimpleNamespace(light=501.0, distance=11.5))

    assert state["level"] == "warning"
    assert state["rag"] == "amber"
    assert "물체가 가까움" in state["alerts"]


def test_judge_hourly_state_uses_requested_thresholds() -> None:
    state = judge_hourly_state(
        SimpleNamespace(
            temperature=28.0,
            humidity=29.0,
            water_level=70.0,
            water_raw=321,
        )
    )

    assert state["level"] == "danger"
    assert state["rag"] == "red"
    assert state["alerts"] == ["온도가 높음", "습도가 낮음", "수위가 낮음"]
    assert state["details"]["water_raw"] == 321


def test_build_realtime_next_action_returns_proactive_greeting_on_distance_entry(monkeypatch) -> None:
    saved_events: list[dict[str, object]] = []
    inside_updates: list[bool] = []

    def fake_save_device_event(payload: dict[str, object]) -> dict[str, object]:
        saved_events.append(payload)
        return {
            "saved": True,
            "event": {
                "event_id": len(saved_events),
                "event_type": payload["event_type"],
            },
        }

    monkeypatch.setattr("services.sensor_policy.save_device_event", fake_save_device_event)
    monkeypatch.setattr("services.sensor_policy.get_db_connection", lambda: _DummyConn())
    monkeypatch.setattr("services.sensor_policy.get_runtime_settings", lambda: _runtime_settings())
    monkeypatch.setattr("services.sensor_policy.set_distance_inside_threshold", lambda inside: inside_updates.append(inside))
    monkeypatch.setattr(
        "services.sensor_policy.can_emit_sensor_warning",
        lambda conn, device_id, now=None: {"allowed": True, "last_warning_at": None, "cooldown_remaining_sec": 0},
    )
    monkeypatch.setattr(
        "services.sensor_policy.can_emit_proactive_greeting",
        lambda conn: {"allowed": True, "last_greeting_at": None, "cooldown_remaining_sec": 0},
    )
    monkeypatch.setattr("services.sensor_policy._resolve_greeting_text", lambda: "안녕? 오늘 하루 어때?")

    payload = SimpleNamespace(
        light=501.0,
        distance=49.0,
        model_dump=lambda: {"distance": 49.0, "light": 501.0},
    )
    result = build_realtime_next_action(
        payload,
        session_id="11111111-1111-1111-1111-111111111111",
        device_id="rp2040-01",
        trigger_source="sensor",
    )

    assert result["type"] == "proactive_greeting"
    assert result["text"] == "안녕? 오늘 하루 어때?"
    assert inside_updates == [True]
    assert [event["event_type"] for event in saved_events] == ["sensor_warning", "proactive_greeting"]
    assert saved_events[0]["status"] == "played"


def test_build_realtime_next_action_skips_when_distance_detection_off(monkeypatch) -> None:
    monkeypatch.setattr(
        "services.sensor_policy.get_runtime_settings",
        lambda: _runtime_settings(distance_detection_enabled=False),
    )
    monkeypatch.setattr("services.sensor_policy.set_distance_inside_threshold", lambda inside: None)

    payload = SimpleNamespace(
        light=501.0,
        distance=49.0,
        model_dump=lambda: {"distance": 49.0, "light": 501.0},
    )

    result = build_realtime_next_action(payload)

    assert result["type"] == "none"
    assert result["reason"] == "distance_detection_disabled"


def test_build_realtime_next_action_skips_when_already_inside(monkeypatch) -> None:
    monkeypatch.setattr(
        "services.sensor_policy.get_runtime_settings",
        lambda: _runtime_settings(distance_inside_threshold=True),
    )

    payload = SimpleNamespace(
        light=501.0,
        distance=49.0,
        model_dump=lambda: {"distance": 49.0, "light": 501.0},
    )

    result = build_realtime_next_action(payload)

    assert result["type"] == "none"
    assert result["reason"] == "distance_already_inside_threshold"


def test_build_realtime_next_action_marks_outside_when_distance_leaves(monkeypatch) -> None:
    inside_updates: list[bool] = []
    monkeypatch.setattr(
        "services.sensor_policy.get_runtime_settings",
        lambda: _runtime_settings(distance_inside_threshold=True),
    )
    monkeypatch.setattr("services.sensor_policy.set_distance_inside_threshold", lambda inside: inside_updates.append(inside))

    payload = SimpleNamespace(
        light=501.0,
        distance=51.0,
        model_dump=lambda: {"distance": 51.0, "light": 501.0},
    )

    result = build_realtime_next_action(payload)

    assert result["type"] == "none"
    assert result["reason"] == "distance_above_threshold"
    assert inside_updates == [False]
