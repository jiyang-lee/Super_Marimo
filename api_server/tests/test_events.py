from fastapi.testclient import TestClient

from main import app


def test_wakeword_event_routes_to_service(monkeypatch) -> None:
    captured: dict[str, object] = {}

    def fake_save_device_event(payload: dict[str, object]) -> dict[str, object]:
        captured.update(payload)
        return {
            "saved": True,
            "event": {
                "event_id": 1,
                "event_type": payload["event_type"],
                "device_id": payload.get("device_id", ""),
            },
        }

    monkeypatch.setattr("routers.events.save_device_event", fake_save_device_event)

    client = TestClient(app)
    response = client.post(
        "/events/wakeword",
        json={
            "device_id": "rp2040-01",
            "trigger_source": "mic-listener",
            "generated_text": "wakeword detected",
            "played": False,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["saved"] is True
    assert payload["event"]["event_type"] == "wakeword"
    assert captured["event_type"] == "wakeword"
    assert captured["device_id"] == "rp2040-01"
    assert captured["trigger_source"] == "mic-listener"


def test_manual_test_event_routes_to_service(monkeypatch) -> None:
    captured: dict[str, object] = {}

    def fake_save_device_event(payload: dict[str, object]) -> dict[str, object]:
        captured.update(payload)
        return {
            "saved": True,
            "event": {
                "event_id": 2,
                "event_type": payload["event_type"],
                "device_id": payload.get("device_id", ""),
            },
        }

    monkeypatch.setattr("routers.events.save_device_event", fake_save_device_event)

    client = TestClient(app)
    response = client.post(
        "/events/manual-test",
        json={
            "device_id": "test-01",
            "trigger_source": "manual",
            "generated_text": "manual test",
            "played": False,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["saved"] is True
    assert payload["event"]["event_type"] == "manual_test"
    assert captured["event_type"] == "manual_test"
    assert captured["device_id"] == "test-01"
    assert captured["trigger_source"] == "manual"
