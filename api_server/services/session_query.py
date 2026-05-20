from typing import Any
from uuid import UUID

from fastapi import HTTPException

from services.session_kind import normalize_session_kind
from utils import normalize_datetime, normalize_response_payload


def list_sessions(conn, limit: int = 20, kind: str = "chat") -> list[dict[str, Any]]:
    resolved_kind = normalize_session_kind(kind)
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT
                s.session_id,
                s.session_kind,
                s.created_at,
                s.last_seen_at,
                s.ended_at,
                s.turn_count,
                s.meta,
                (
                    SELECT content
                    FROM session_message sm
                    WHERE sm.session_id = s.session_id
                      AND sm.role = 'user'
                    ORDER BY sm.message_id ASC
                    LIMIT 1
                ) AS first_user_message,
                (
                    SELECT content
                    FROM session_message sm
                    WHERE sm.session_id = s.session_id
                    ORDER BY sm.created_at DESC
                    LIMIT 1
                ) AS last_message,
                (
                    SELECT created_at
                    FROM session_message sm
                    WHERE sm.session_id = s.session_id
                    ORDER BY sm.created_at DESC
                    LIMIT 1
                ) AS last_message_at,
                (
                    SELECT COUNT(*)
                    FROM session_message sm
                    WHERE sm.session_id = s.session_id
                ) AS message_count
            FROM session s
            WHERE (s.meta IS NULL OR COALESCE((s.meta->>'is_test')::boolean, false) = false)
              AND s.session_kind = %s
            ORDER BY s.last_seen_at DESC
            LIMIT %s
            """,
            (resolved_kind, limit),
        )
        rows = cur.fetchall() or []

    sessions: list[dict[str, Any]] = []
    for row in rows:
        first_user = (row.get("first_user_message") or "").strip()
        last_message = (row.get("last_message") or "").strip()
        preview = first_user or last_message or "New chat"
        sessions.append(
            {
                "session_id": str(row["session_id"]),
                "session_kind": str(row.get("session_kind") or resolved_kind),
                "created_at": normalize_datetime(row["created_at"]),
                "last_seen_at": normalize_datetime(row["last_seen_at"]),
                "ended_at": normalize_datetime(row["ended_at"]) if row.get("ended_at") else None,
                "turn_count": row["turn_count"],
                "message_count": row["message_count"],
                "title": preview[:20],
                "preview": preview[:80],
                "last_message_at": normalize_datetime(row["last_message_at"]) if row.get("last_message_at") else None,
            }
        )
    return sessions


def fetch_session_detail(conn, session_id: UUID) -> dict[str, Any]:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT session_id, created_at, last_seen_at, ended_at, turn_count, meta
            FROM session
            WHERE session_id = %s
            """,
            (session_id,),
        )
        session_row = cur.fetchone()
        if session_row is None:
            raise HTTPException(status_code=404, detail="session not found")

        cur.execute(
            """
            SELECT message_id, session_id, role, content, created_at, meta
            FROM session_message
            WHERE session_id = %s
            ORDER BY message_id ASC
            """,
            (session_id,),
        )
        message_rows = cur.fetchall() or []

    messages: list[dict[str, Any]] = []
    for row in message_rows:
        messages.append(
            {
                "message_id": row["message_id"],
                "session_id": str(row["session_id"]),
                "role": row["role"],
                "content": row["content"],
                "created_at": normalize_datetime(row["created_at"]),
                "meta": normalize_response_payload(row["meta"]),
            }
        )

    return {
        "session": {
            "session_id": str(session_row["session_id"]),
            "created_at": normalize_datetime(session_row["created_at"]),
            "last_seen_at": normalize_datetime(session_row["last_seen_at"]),
            "ended_at": normalize_datetime(session_row["ended_at"]) if session_row.get("ended_at") else None,
            "turn_count": session_row["turn_count"],
            "meta": normalize_response_payload(session_row["meta"]),
        },
        "messages": messages,
    }
