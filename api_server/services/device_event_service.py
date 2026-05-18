from typing import Any

from fastapi import HTTPException
from psycopg.types.json import Json

from extensions.db import get_db_connection
from utils import normalize_datetime, normalize_response_payload

ALLOWED_EVENT_TYPES = {"wakeword", "manual_test"}


def save_device_event(payload: dict[str, Any]) -> dict[str, Any]:
    event_type = str(payload.get("event_type") or "").strip()
    if not event_type:
        raise HTTPException(status_code=400, detail="event_type is required")
    if event_type not in ALLOWED_EVENT_TYPES:
        raise HTTPException(status_code=400, detail="unsupported event_type")

    sensor = payload.get("sensor") or {}
    distance = payload.get("distance")
    if distance is None and isinstance(sensor, dict):
        distance = sensor.get("distance")

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
                    Json(payload.get("meta") or {}),
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
