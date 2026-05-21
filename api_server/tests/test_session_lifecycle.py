from datetime import datetime, timezone
from uuid import UUID

import pytest

from services.session_lifecycle import ensure_session


class _FakeCursor:
    def __init__(self, rows):
        self.rows = list(rows)
        self.executed = []

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def execute(self, sql, params):  # noqa: ANN001
        self.executed.append((sql, params))

    def fetchone(self):
        if not self.rows:
            return None
        return self.rows.pop(0)


class _FakeConn:
    def __init__(self, rows):
        self.cursor_obj = _FakeCursor(rows)

    def cursor(self):
        return self.cursor_obj


def test_ensure_session_rejects_ended_session() -> None:
    session_id = UUID("11111111-1111-1111-1111-111111111111")
    conn = _FakeConn([
        None,
        None,
        {"ended_at": datetime(2026, 5, 21, tzinfo=timezone.utc)},
    ])

    with pytest.raises(Exception) as exc_info:
        ensure_session(conn, session_id, session_kind="voice")

    assert getattr(exc_info.value, "status_code", None) == 409


def test_ensure_session_updates_active_session() -> None:
    session_id = UUID("11111111-1111-1111-1111-111111111111")
    conn = _FakeConn([
        None,
        {
            "session_id": session_id,
            "created_at": None,
            "last_seen_at": None,
            "ended_at": None,
            "turn_count": 1,
            "meta": {},
            "session_kind": "voice",
        },
    ])

    row, created = ensure_session(conn, session_id, session_kind="voice")

    assert created is False
    assert row["session_id"] == session_id
