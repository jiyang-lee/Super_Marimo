from datetime import datetime, timezone

import services.device_event_service as service


class _FakeCursor:
    def __init__(self, rows):
        self.rows = rows
        self.executed = []

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def execute(self, sql, params):
        self.executed.append((sql, params))

    def fetchall(self):
        return self.rows


class _FakeConn:
    def __init__(self, rows):
        self.cursor_obj = _FakeCursor(rows)
        self.committed = False

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def cursor(self):
        return self.cursor_obj

    def commit(self):
        self.committed = True


def test_list_events_supports_multi_type_ascending_order(monkeypatch) -> None:
    rows = [
        {
            "event_id": 11,
            "session_id": None,
            "created_at": datetime(2026, 5, 18, 12, 0, tzinfo=timezone.utc),
            "event_type": "sensor_warning",
            "device_id": "rp2040-01",
            "trigger_source": "sensor",
            "distance": 8.0,
            "sensor_json": {"distance": 8.0},
            "state_level": "warning",
            "state_alerts": ["close"],
            "generated_text": "first event",
            "played": False,
            "status": "pending",
            "meta": {"kind": "warning"},
        }
    ]
    fake_conn = _FakeConn(rows)
    monkeypatch.setattr(service, "get_db_connection", lambda: fake_conn)

    payload = service.list_events(
        event_type="manual-test",
        event_types=["wakeword", "sensor-warning"],
        played=False,
        limit=10,
        offset=0,
        order="asc",
    )

    assert payload["count"] == 1
    assert payload["limit"] == 10
    assert payload["offset"] == 0
    assert payload["events"][0]["event_type"] == "sensor_warning"

    sql, params = fake_conn.cursor_obj.executed[0]
    assert "event_type IN (%s, %s, %s)" in sql
    assert "ORDER BY created_at ASC" in sql
    assert params == ("manual_test", "wakeword", "sensor_warning", False, 10, 0)


def test_list_events_supports_status_filter(monkeypatch) -> None:
    rows = [
        {
            "event_id": 12,
            "session_id": None,
            "created_at": datetime(2026, 5, 18, 12, 0, tzinfo=timezone.utc),
            "event_type": "sensor_warning",
            "device_id": "rp2040-01",
            "trigger_source": "sensor",
            "distance": 8.0,
            "sensor_json": {"distance": 8.0},
            "state_level": "warning",
            "state_alerts": ["close"],
            "generated_text": "processing event",
            "played": False,
            "status": "pending",
            "meta": {"kind": "warning"},
        }
    ]
    fake_conn = _FakeConn(rows)
    monkeypatch.setattr(service, "get_db_connection", lambda: fake_conn)

    payload = service.list_events(status="pending", limit=5, offset=0)

    assert payload["count"] == 1
    assert payload["events"][0]["status"] == "pending"

    sql, params = fake_conn.cursor_obj.executed[0]
    assert "status = %s" in sql
    assert params == ("pending", 5, 0)
