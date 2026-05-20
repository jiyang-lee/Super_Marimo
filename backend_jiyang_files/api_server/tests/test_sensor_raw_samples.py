from importlib import util
from pathlib import Path

from fastapi.testclient import TestClient

import routers.sensor as sensor_router


API_MAIN_PATH = Path(__file__).resolve().parents[1] / "main.py"
spec = util.spec_from_file_location("api_server_main_test_sensor", API_MAIN_PATH)
assert spec is not None and spec.loader is not None
api_main = util.module_from_spec(spec)
spec.loader.exec_module(api_main)
app = api_main.app


def test_realtime_ingest_saves_basic_sensor_fields(monkeypatch) -> None:
    captured: dict[str, object] = {}

    def fake_save_sensor_reading(payload, sensor_type, state):
        captured["payload"] = payload
        captured["sensor_type"] = sensor_type
        captured["state"] = state
        return {"saved": True, "reading_id": 1}

    monkeypatch.setattr(sensor_router, "save_sensor_reading", fake_save_sensor_reading)
    monkeypatch.setattr(sensor_router, "_safe_build_realtime_next_action", lambda payload: {"type": "none"})

    client = TestClient(app)
    response = client.post(
        "/sensor/realtime-ingest",
        json={
            "temperature": 25.5,
            "humidity": 54.0,
            "light": 420.0,
            "distance": 49.0,
            "water_level": 72.0,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert captured["sensor_type"] == "realtime"
    assert captured["payload"]["temperature"] == 25.5
    assert captured["payload"]["humidity"] == 54.0
    assert captured["payload"]["light"] == 420.0
    assert captured["payload"]["distance"] == 49.0
    assert captured["payload"]["water_level"] == 72.0
