from typing import Any, Literal, Optional

from fastapi import HTTPException
from psycopg.types.json import Json

from config import DEVICE_EVENT_TYPES
from extensions.db import get_db_connection
from utils import normalize_datetime, normalize_response_payload

EVENT_TYPE_ALIASES = {
    "manual-test": "manual_test",
    "sensor-warning": "sensor_warning",
}


def normalize_event_type(event_type: str) -> str:
    value = str(event_type or "").strip().lower().replace(" ", "_")
    value = EVENT_TYPE_ALIASES.get(value, value)
    return value


def save_device_event(payload: dict[str, Any]) -> dict[str, Any]:
    event_type = normalize_event_type(payload.get("event_type") or "")
    if not event_type:
        raise HTTPException(status_code=400, detail="event_type is required")
    if event_type not in DEVICE_EVENT_TYPES:
        raise HTTPException(status_code=400, detail="unsupported event_type")

    sensor = payload.get("sensor") or payload.get("sensor_json") or {}
    distance = payload.get("distance")
    if distance is None and isinstance(sensor, dict):
        distance = sensor.get("distance")
    meta = dict(payload.get("meta") or {})
    next_action = payload.get("next_action")
    if next_action is not None:
        meta.setdefault("next_action", next_action)

    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO device_event_log (
                    session_id,
                    event_type,
                    device_id,
                    trigger_source,
                    distance,
                    sensor_json,
                    state_level,
                    state_alerts,
                    generated_text,
                    played,
                    meta
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING
                    event_id,
                    session_id,
                    created_at,
                    event_type,
                    device_id,
                    trigger_source,
                    distance,
                    sensor_json,
                    state_level,
                    state_alerts,
                    generated_text,
                    played,
                    meta
                """,
                (
                    payload.get("session_id"),
                    event_type,
                    str(payload.get("device_id") or "").strip(),
                    str(payload.get("trigger_source") or "manual").strip() or "manual",
                    distance,
                    Json(sensor or {}),
                    str(payload.get("state_level") or "normal").strip() or "normal",
                    Json(payload.get("state_alerts") or []),
                    str(payload.get("generated_text") or ""),
                    bool(payload.get("played", False)),
                    Json(meta),
                ),
            )
            row = cur.fetchone()
        conn.commit()

    if row is None:
        raise HTTPException(status_code=500, detail="device event could not be saved")

    event = {
        "event_id": row["event_id"],
        "session_id": str(row["session_id"]) if row.get("session_id") else None,
        "created_at": normalize_datetime(row["created_at"]),
        "event_type": row["event_type"],
        "device_id": row["device_id"],
        "trigger_source": row["trigger_source"],
        "distance": row["distance"],
        "sensor": normalize_response_payload(row["sensor_json"]),
        "state_level": row["state_level"],
        "state_alerts": normalize_response_payload(row["state_alerts"]),
        "generated_text": row["generated_text"],
        "played": row["played"],
        "meta": normalize_response_payload(row["meta"]),
    }
    return {"saved": True, "event": normalize_response_payload(event)}


def list_events(
    *,
    event_type: Optional[str] = None,
    event_types: Optional[list[str]] = None,
    device_id: Optional[str] = None,
    played: Optional[bool] = None,
    limit: int = 50,
    offset: int = 0,
    order: Literal["asc", "desc"] = "desc",
) -> dict[str, Any]:
    safe_limit = max(1, min(limit, 200))
    safe_offset = max(0, offset)

    conditions: list[str] = []
    params: list[Any] = []

    normalized_types: list[str] = []
    if event_type:
        normalized_types.append(normalize_event_type(event_type))
    if event_types:
        normalized_types.extend(
            normalized
            for normalized in (normalize_event_type(item) for item in event_types)
            if normalized
        )
    if normalized_types:
        unique_types = list(dict.fromkeys(normalized_types))
        if len(unique_types) == 1:
            conditions.append("event_type = %s")
            params.append(unique_types[0])
        else:
            placeholders = ", ".join(["%s"] * len(unique_types))
            conditions.append(f"event_type IN ({placeholders})")
            params.extend(unique_types)
    if device_id:
        conditions.append("device_id = %s")
        params.append(device_id)
    if played is not None:
        conditions.append("played = %s")
        params.append(played)

    where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""
    order_clause = "ASC" if order == "asc" else "DESC"

    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                f"""
                SELECT
                    event_id,
                    session_id,
                    created_at,
                    event_type,
                    device_id,
                    trigger_source,
                    distance,
                    sensor_json,
                    state_level,
                    state_alerts,
                    generated_text,
                    played,
                    meta
                FROM device_event_log
                {where_clause}
                ORDER BY created_at {order_clause}
                LIMIT %s OFFSET %s
                """,
                (*params, safe_limit, safe_offset),
            )
            rows = cur.fetchall() or []

    events: list[dict[str, Any]] = []
    for row in rows:
        events.append(
            {
                "event_id": row["event_id"],
                "session_id": str(row["session_id"]) if row.get("session_id") else None,
                "created_at": normalize_datetime(row["created_at"]),
                "event_type": row["event_type"],
                "device_id": row["device_id"],
                "trigger_source": row["trigger_source"],
                "distance": row["distance"],
                "sensor": normalize_response_payload(row["sensor_json"]),
                "state_level": row["state_level"],
                "state_alerts": normalize_response_payload(row["state_alerts"]),
                "generated_text": row["generated_text"],
                "played": row["played"],
                "meta": normalize_response_payload(row["meta"]),
            }
        )

    return {
        "events": normalize_response_payload(events),
        "limit": safe_limit,
        "offset": safe_offset,
        "count": len(events),
    }


def get_event(event_id: int) -> dict[str, Any]:
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    event_id,
                    session_id,
                    created_at,
                    event_type,
                    device_id,
                    trigger_source,
                    distance,
                    sensor_json,
                    state_level,
                    state_alerts,
                    generated_text,
                    played,
                    meta
                FROM device_event_log
                WHERE event_id = %s
                """,
                (event_id,),
            )
            row = cur.fetchone()

    if row is None:
        raise HTTPException(status_code=404, detail="event not found")

    return normalize_response_payload(
        {
            "event_id": row["event_id"],
            "session_id": str(row["session_id"]) if row.get("session_id") else None,
            "created_at": normalize_datetime(row["created_at"]),
            "event_type": row["event_type"],
            "device_id": row["device_id"],
            "trigger_source": row["trigger_source"],
            "distance": row["distance"],
            "sensor": normalize_response_payload(row["sensor_json"]),
            "state_level": row["state_level"],
            "state_alerts": normalize_response_payload(row["state_alerts"]),
            "generated_text": row["generated_text"],
            "played": row["played"],
            "meta": normalize_response_payload(row["meta"]),
        }
    )


def mark_event_played(event_id: int) -> dict[str, Any]:
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE device_event_log
                SET played = TRUE
                WHERE event_id = %s
                RETURNING
                    event_id,
                    session_id,
                    created_at,
                    event_type,
                    device_id,
                    trigger_source,
                    distance,
                    sensor_json,
                    state_level,
                    state_alerts,
                    generated_text,
                    played,
                    meta
                """,
                (event_id,),
            )
            row = cur.fetchone()
        conn.commit()

    if row is None:
        raise HTTPException(status_code=404, detail="event not found")

    return normalize_response_payload(
        {
            "event_id": row["event_id"],
            "session_id": str(row["session_id"]) if row.get("session_id") else None,
            "created_at": normalize_datetime(row["created_at"]),
            "event_type": row["event_type"],
            "device_id": row["device_id"],
            "trigger_source": row["trigger_source"],
            "distance": row["distance"],
            "sensor": normalize_response_payload(row["sensor_json"]),
            "state_level": row["state_level"],
            "state_alerts": normalize_response_payload(row["state_alerts"]),
            "generated_text": row["generated_text"],
            "played": row["played"],
            "meta": normalize_response_payload(row["meta"]),
        }
    )
