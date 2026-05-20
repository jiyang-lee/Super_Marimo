from importlib import util
from pathlib import Path
from datetime import datetime, timezone

from fastapi.testclient import TestClient

import routers.sensor as sensor_router
import services.sensor_store as sensor_store


API_MAIN_PATH = Path(__file__).resolve().parents[1] / "main.py"
spec = util.spec_from_file_location("api_server_main_test_sensor", API_MAIN_PATH)
assert spec is not None and spec.loader is not None
api_main = util.module_from_spec(spec)
spec.loader.exec_module(api_main)
app = api_main.app


class _FakeCursor:
    def __init__(self) -> None:
        self.executed = []

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def execute(self, sql, params):
        self.executed.append((sql, params))

    def fetchone(self):
        return {
            "sample_id": 7,
            "created_at": datetime(2026, 5, 19, 14, 0, tzinfo=timezone.utc),
            "raw_value": 321,
            "last_at": None,
        }


class _FakeConn:
    def __init__(self) -> None:
        self.cursor_obj = _FakeCursor()
        self.committed = False

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def cursor(self):
        return self.cursor_obj

    def commit(self):
        self.committed = True


def test_hourly_ingest_saves_light_raw_sample(monkeypatch) -> None:
    captured: dict[str, object] = {}

    def fake_save_sensor_reading(payload, sensor_type, state):
        captured["payload"] = payload
        captured["sensor_type"] = sensor_type
        captured["state"] = state
        return {"saved": True, "reading_id": 1}

    monkeypatch.setattr(sensor_router, "save_sensor_reading", fake_save_sensor_reading)
    monkeypatch.setattr(sensor_router, "save_water_raw_sample", lambda raw_value: {"table": "water_raw_samples", "raw_value": raw_value})
    monkeypatch.setattr(sensor_router, "save_light_raw_sample", lambda raw_value: {"table": "light_raw_samples", "raw_value": raw_value})

    client = TestClient(app)
    response = client.post(
        "/sensor/hourly-ingest",
        json={
            "temperature": 26.0,
            "humidity": 49.0,
            "water_level": 80.0,
            "water_raw": 333,
            "light_raw": 1234,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["water_raw_sample"]["table"] == "water_raw_samples"
    assert payload["light_raw_sample"]["table"] == "light_raw_samples"
    assert captured["sensor_type"] == "hourly"
    assert captured["payload"]["light_raw"] == 1234


def test_save_light_raw_sample_uses_light_table(monkeypatch) -> None:
    fake_conn = _FakeConn()
    monkeypatch.setattr(sensor_store, "get_db_connection", lambda: fake_conn)

    result = sensor_store.save_light_raw_sample(321)

    assert result["table"] == "light_raw_samples"
    assert fake_conn.committed is True
    insert_executed = [e for e in fake_conn.cursor_obj.executed if "INSERT INTO light_raw_samples" in e[0]]
    assert len(insert_executed) == 1
    sql, params = insert_executed[0]
    assert params == (321,)
