from typing import Any, Optional
from uuid import UUID

from fastapi import HTTPException
from psycopg.types.json import Json

from config import SESSION_HISTORY_LIMIT
from services.session_kind import normalize_session_kind
from utils import normalize_datetime, normalize_response_payload


def ensure_session(conn, session_id: UUID, session_kind: Optional[str] = None) -> tuple[dict[str, Any], bool]:
    resolved_session_kind = normalize_session_kind(session_kind)
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO session (session_id, session_kind)
            VALUES (%s, %s)
            ON CONFLICT DO NOTHING
            RETURNING session_id, created_at, last_seen_at, ended_at, turn_count, meta, session_kind
            """,
            (session_id, resolved_session_kind),
        )
        row = cur.fetchone()
        if row is not None:
            return row, True

        cur.execute(
            """
            UPDATE session
            SET last_seen_at = NOW(),
                session_kind = COALESCE(session_kind, %s)
            WHERE session_id = %s
              AND ended_at IS NULL
            RETURNING session_id, created_at, last_seen_at, ended_at, turn_count, meta, session_kind
            """,
            (resolved_session_kind, session_id),
        )
        row = cur.fetchone()
        if row is None:
            cur.execute(
                """
                SELECT ended_at
                FROM session
                WHERE session_id = %s
                """,
                (session_id,),
            )
            existing = cur.fetchone()
            if existing is not None and existing.get("ended_at") is not None:
                raise HTTPException(status_code=409, detail="session has already ended")
            raise HTTPException(status_code=500, detail="session row could not be created")
        return row, False


def save_session_message(
    conn,
    session_id: UUID,
    role: str,
    content: str,
    meta: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO session_message (session_id, role, content, meta)
            VALUES (%s, %s, %s, %s)
            RETURNING message_id, created_at
            """,
            (session_id, role, content, Json(meta or {})),
        )
        row = cur.fetchone()
    if row is None:
        raise HTTPException(status_code=500, detail="session message could not be saved")
    return row


def fetch_recent_session_messages(
    conn,
    session_id: UUID,
    limit: int = SESSION_HISTORY_LIMIT,
) -> list[dict[str, str]]:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT role, content
            FROM session_message
            WHERE session_id = %s
            ORDER BY message_id ASC
            LIMIT %s
            """,
            (session_id, limit),
        )
        rows = cur.fetchall() or []

    history: list[dict[str, str]] = []
    for row in rows:
        role = (row.get("role") or "").strip().lower()
        content = (row.get("content") or "").strip()
        if role in {"user", "assistant", "system"} and content:
            history.append({"role": role, "content": content})
    return history


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


def update_session_turn(conn, session_id: UUID) -> dict[str, Any]:
    with conn.cursor() as cur:
        cur.execute(
            """
            UPDATE session
            SET last_seen_at = NOW(),
                turn_count = turn_count + 1
            WHERE session_id = %s
            RETURNING session_id, session_kind, created_at, last_seen_at, ended_at, turn_count, meta
            """,
            (session_id,),
        )
        row = cur.fetchone()
    if row is None:
        raise HTTPException(status_code=500, detail="session turn could not be updated")
    return row


def end_session(conn, session_id: UUID, meta: Optional[dict[str, Any]] = None) -> dict[str, Any]:
    with conn.cursor() as cur:
        cur.execute(
            """
            UPDATE session
            SET ended_at = NOW(),
                last_seen_at = NOW(),
                meta = meta || %s::jsonb
            WHERE session_id = %s
            RETURNING session_id, session_kind, created_at, last_seen_at, ended_at, turn_count, meta
            """,
            (Json(meta or {}), session_id),
        )
        row = cur.fetchone()
    if row is None:
        raise HTTPException(status_code=500, detail="session could not be ended")
    return row
