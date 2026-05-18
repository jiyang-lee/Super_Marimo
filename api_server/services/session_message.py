from typing import Any, Optional
from uuid import UUID

from fastapi import HTTPException
from psycopg.types.json import Json

from config import SESSION_HISTORY_LIMIT


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
            ORDER BY created_at DESC
            LIMIT %s
            """,
            (session_id, limit),
        )
        rows = cur.fetchall() or []

    history: list[dict[str, str]] = []
    for row in reversed(rows):
        role = (row.get("role") or "").strip().lower()
        content = (row.get("content") or "").strip()
        if role in {"user", "assistant", "system"} and content:
            history.append({"role": role, "content": content})
    return history
