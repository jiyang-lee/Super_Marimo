from importlib import util
from pathlib import Path

from fastapi.testclient import TestClient

import routers.events as events_router


API_MAIN_PATH = Path(__file__).resolve().parents[1] / "main.py"
spec = util.spec_from_file_location("api_server_main_test", API_MAIN_PATH)
assert spec is not None and spec.loader is not None
api_main = util.module_from_spec(spec)
spec.loader.exec_module(api_main)
app = api_main.app


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

    monkeypatch.setattr(events_router, "save_device_event", fake_save_device_event)

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


def test_device_event_routes_to_service(monkeypatch) -> None:
    captured: dict[str, object] = {}

    def fake_save_device_event(payload: dict[str, object]) -> dict[str, object]:
        captured.update(payload)
        return {
            "saved": True,
            "event": {
                "event_id": 3,
                "event_type": payload["event_type"],
                "device_id": payload.get("device_id", ""),
            },
        }

    monkeypatch.setattr(events_router, "save_device_event", fake_save_device_event)

    client = TestClient(app)
    response = client.post(
        "/events",
        json={
            "event_type": "speech_started",
            "device_id": "serial-01",
            "trigger_source": "serial_voice_proto",
            "generated_text": "speech started",
            "played": False,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["saved"] is True
    assert payload["event"]["event_type"] == "speech_started"
    assert captured["event_type"] == "speech_started"
    assert captured["device_id"] == "serial-01"
    assert captured["trigger_source"] == "serial_voice_proto"


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

    monkeypatch.setattr(events_router, "save_device_event", fake_save_device_event)

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


def test_update_event_status_routes_to_service(monkeypatch) -> None:
    captured: dict[str, object] = {}

    def fake_update_event_status(event_id: int, status: str) -> dict[str, object]:
        captured["event_id"] = event_id
        captured["status"] = status
        return {
            "event_id": event_id,
            "status": status,
            "played": status in {"playing", "played"},
        }

    monkeypatch.setattr(events_router, "update_event_status", fake_update_event_status)

    client = TestClient(app)
    response = client.put(
        "/events/7/status",
        json={"status": "processing"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["event_id"] == 7
    assert payload["status"] == "processing"
    assert captured["event_id"] == 7
    assert captured["status"] == "processing"
