from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from services.session_message import fetch_recent_session_messages
from services.session_query import fetch_session_detail


class _DualResultCursor:
    def __init__(self, session_row, message_rows):
        self._session_row = session_row
        self._message_rows = message_rows
        self.sql_log: list[str] = []
        self.params_log: list[tuple[object, ...]] = []
        self._fetch_index = 0

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def execute(self, sql, params):
        self.sql_log.append(sql)
        self.params_log.append(params)

    def fetchone(self):
        self._fetch_index += 1
        return self._session_row

    def fetchall(self):
        self._fetch_index += 1
        return self._message_rows


class _FetchAllCursor:
    def __init__(self, rows):
        self.rows = rows
        self.sql = ""
        self.params = ()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def execute(self, sql, params):
        self.sql = sql
        self.params = params

    def fetchall(self):
        return self.rows


class _Conn:
    def __init__(self, cursor):
        self._cursor = cursor

    def cursor(self):
        return self._cursor


def test_fetch_recent_session_messages_returns_ascending_messages() -> None:
    rows = [
        {"role": "user", "content": "첫째"},
        {"role": "assistant", "content": "둘째"},
        {"role": "assistant", "content": "셋째"},
    ]
    cursor = _FetchAllCursor(rows)
    conn = _Conn(cursor)

    history = fetch_recent_session_messages(conn, UUID("11111111-1111-1111-1111-111111111111"), limit=50)

    assert "ORDER BY message_id ASC" in cursor.sql
    assert [item["content"] for item in history] == ["첫째", "둘째", "셋째"]


def test_fetch_session_detail_returns_messages_in_chronological_order() -> None:
    session_row = {
        "session_id": UUID("11111111-1111-1111-1111-111111111111"),
        "created_at": datetime(2026, 1, 1, tzinfo=timezone.utc),
        "last_seen_at": datetime(2026, 1, 1, tzinfo=timezone.utc),
        "ended_at": None,
        "turn_count": 2,
        "meta": {},
    }
    message_rows = [
        {
            "message_id": 1,
            "session_id": session_row["session_id"],
            "role": "user",
            "content": "첫째",
            "created_at": datetime(2026, 1, 1, 0, 0, tzinfo=timezone.utc),
            "meta": {},
        },
        {
            "message_id": 2,
            "session_id": session_row["session_id"],
            "role": "assistant",
            "content": "둘째",
            "created_at": datetime(2026, 1, 1, 0, 1, tzinfo=timezone.utc),
            "meta": {},
        },
    ]
    cursor = _DualResultCursor(session_row, message_rows)
    conn = _Conn(cursor)

    payload = fetch_session_detail(conn, session_row["session_id"])

    assert "ORDER BY message_id ASC" in cursor.sql_log[-1]
    assert [item["content"] for item in payload["messages"]] == ["첫째", "둘째"]
