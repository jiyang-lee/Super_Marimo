from typing import Any, Optional
from uuid import UUID

from fastapi import HTTPException
from psycopg.types.json import Json

from services.session_kind import normalize_session_kind


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
            RETURNING session_id, created_at, last_seen_at, ended_at, turn_count, meta, session_kind
            """,
            (resolved_session_kind, session_id),
        )
        row = cur.fetchone()
        if row is None:
            raise HTTPException(status_code=500, detail="session row could not be created")
        return row, False


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


def update_session_meta(conn, session_id: UUID, meta_patch: dict[str, Any]) -> dict[str, Any]:
    with conn.cursor() as cur:
        cur.execute(
            """
            UPDATE session
            SET last_seen_at = NOW(),
                meta = COALESCE(meta, '{}'::jsonb) || %s::jsonb
            WHERE session_id = %s
            RETURNING session_id, session_kind, created_at, last_seen_at, ended_at, turn_count, meta
            """,
            (Json(meta_patch or {}), session_id),
        )
        row = cur.fetchone()
    if row is None:
        raise HTTPException(status_code=500, detail="session meta could not be updated")
    return row


def end_session(conn, session_id: UUID, meta: Optional[dict[str, Any]] = None) -> dict[str, Any]:
    with conn.cursor() as cur:
        cur.execute(
            """
            UPDATE session
            SET ended_at = NOW(),
                last_seen_at = NOW(),
                meta = COALESCE(meta, '{}'::jsonb) || %s::jsonb
            WHERE session_id = %s
            RETURNING session_id, session_kind, created_at, last_seen_at, ended_at, turn_count, meta
            """,
            (Json(meta or {}), session_id),
        )
        row = cur.fetchone()
    if row is None:
        raise HTTPException(status_code=500, detail="session could not be ended")
    return row


def delete_session(conn, session_id: UUID) -> bool:
    with conn.cursor() as cur:
        cur.execute(
            """
            DELETE FROM session
            WHERE session_id = %s
            """,
            (session_id,),
        )
        return cur.rowcount > 0
