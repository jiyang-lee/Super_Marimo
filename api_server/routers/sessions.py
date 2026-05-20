from typing import Any
from uuid import UUID

from fastapi import APIRouter
from pydantic import BaseModel, Field

from extensions.db import get_db_connection
from services.session_lifecycle import ensure_session, end_session
from services.session_message import fetch_recent_session_messages, save_session_message
from services.session_query import fetch_session_detail, list_sessions
from utils import normalize_response_payload

router = APIRouter()


class SessionMessagePayload(BaseModel):
    role: str = Field(..., description="user | assistant | system")
    content: str = Field(..., description="message content")
    meta: dict[str, Any] = Field(default_factory=dict)


@router.get("/sessions")
def sessions(limit: int = 20) -> dict[str, Any]:
    safe_limit = max(1, min(limit, 100))
    with get_db_connection() as conn:
        rows = list_sessions(conn, safe_limit)
    return {"sessions": normalize_response_payload(rows)}


@router.get("/sessions/{session_id}")
def session_detail(session_id: UUID) -> dict[str, Any]:
    with get_db_connection() as conn:
        payload = fetch_session_detail(conn, session_id)
    return normalize_response_payload(payload)


@router.post("/sessions/{session_id}/touch")
def session_touch(session_id: UUID) -> dict[str, Any]:
    with get_db_connection() as conn:
        payload, created = ensure_session(conn, session_id)
        conn.commit()
    return normalize_response_payload(
        {
            "session": {
                "session_id": str(payload["session_id"]),
                "created_at": payload["created_at"],
                "last_seen_at": payload["last_seen_at"],
                "ended_at": payload["ended_at"],
                "turn_count": payload["turn_count"],
                "meta": payload["meta"],
            },
            "created": created,
        }
    )


@router.post("/sessions/{session_id}/end")
def session_end(session_id: UUID) -> dict[str, Any]:
    with get_db_connection() as conn:
        payload = end_session(conn, session_id, meta={"ended_by": "serial_voice_proto"})
        conn.commit()
    return normalize_response_payload(
        {
            "session": {
                "session_id": str(payload["session_id"]),
                "created_at": payload["created_at"],
                "last_seen_at": payload["last_seen_at"],
                "ended_at": payload["ended_at"],
                "turn_count": payload["turn_count"],
                "meta": payload["meta"],
            }
        }
    )


@router.post("/sessions/{session_id}/messages")
def session_save_message(session_id: UUID, payload: SessionMessagePayload) -> dict[str, Any]:
    with get_db_connection() as conn:
        ensure_session(conn, session_id)
        row = save_session_message(conn, session_id, payload.role, payload.content, meta=payload.meta)
        conn.commit()
    return normalize_response_payload({
        "saved": True,
        "message_id": row["message_id"],
        "created_at": row["created_at"],
        "session_id": str(session_id),
    })


@router.get("/sessions/{session_id}/messages")
def session_get_messages(session_id: UUID, limit: int = 50) -> dict[str, Any]:
    with get_db_connection() as conn:
        history = fetch_recent_session_messages(conn, session_id, limit=limit)
    return normalize_response_payload({
        "session_id": str(session_id),
        "limit": limit,
        "count": len(history),
        "messages": history,
    })
