from typing import Any, Optional

from fastapi import HTTPException
from psycopg.types.json import Json

from extensions.db import cleanup_old_realtime_rows, get_db_connection
from schemas import SensorPayload
from services.sensor_analytics import build_sensor_payload, build_sensor_semantics, build_sensor_summary, compute_sensor_metrics
from services.sensor_judge import judge_sensor_state
from utils import normalize_datetime, normalize_response_payload


def default_sensor_payload() -> SensorPayload:
    return SensorPayload(
        temperature=23.0,
        humidity=50.0,
        light=500.0,
        water_level=50.0,
        distance=100.0,
    )


def extract_payload(row: Optional[dict[str, Any]]) -> dict[str, Any]:
    if row is None:
        return {}
    payload = row.get("payload") or {}
    return dict(payload)


def expand_sensor_row(row: Optional[dict[str, Any]]) -> Optional[dict[str, Any]]:
    if row is None:
        return None
    payload = extract_payload(row)
    return {
        "reading_id": row["reading_id"],
        "created_at": normalize_datetime(row["created_at"]),
        "sensor_type": row["sensor_type"],
        **payload,
        "state_level": row["state_level"],
        "alerts": row["state_alerts"],
    }


def get_latest_sensor_row(conn, sensor_type: str) -> Optional[dict[str, Any]]:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT reading_id, created_at, sensor_type, payload, state_level, state_alerts
            FROM sensor_readings
            WHERE sensor_type = %s
            ORDER BY created_at DESC
            LIMIT 1
            """,
            (sensor_type,),
        )
        return cur.fetchone()


def get_recent_sensor_rows(conn, sensor_type: str, limit: int = 24) -> list[dict[str, Any]]:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT reading_id, created_at, sensor_type, payload, state_level, state_alerts
            FROM sensor_readings
            WHERE sensor_type = %s
            ORDER BY created_at DESC
            LIMIT %s
            """,
            (sensor_type, limit),
        )
        rows = cur.fetchall() or []

    history: list[dict[str, Any]] = []
    for row in reversed(rows):
        history.append(expand_sensor_row(row))
    return history


def load_latest_sensor_payload() -> SensorPayload:
    fallback = default_sensor_payload().model_dump()
    try:
        with get_db_connection() as conn:
            realtime_row = get_latest_sensor_row(conn, "realtime")
            hourly_row = get_latest_sensor_row(conn, "hourly")
            metrics = compute_sensor_metrics(
                conn,
                current_payload=None,
                current_sensor_type=None,
            )
    except Exception:
        return default_sensor_payload()

    realtime_payload = extract_payload(realtime_row)
    hourly_payload = extract_payload(hourly_row)

    merged = build_sensor_payload(realtime_payload, hourly_payload, metrics=metrics)
    state = judge_sensor_state(SensorPayload(**merged), metrics=metrics)
    merged["sensor_semantics"] = build_sensor_semantics(metrics)
    merged["sensor_summary"] = build_sensor_summary(merged, state, metrics)
    fallback.update(merged)
    return SensorPayload(**fallback)


def save_sensor_reading(
    payload: dict[str, Any],
    sensor_type: str,
    state: dict[str, Any],
) -> dict[str, Any]:
    deleted_count = cleanup_old_realtime_rows() if sensor_type == "realtime" else 0
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO sensor_readings (
                    sensor_type, payload, state_level, state_alerts
                )
                VALUES (%s, %s, %s, %s)
                RETURNING reading_id, created_at
                """,
                (
                    sensor_type,
                    Json(payload),
                    state["level"],
                    Json(state["alerts"]),
                ),
            )
            row = cur.fetchone()
        conn.commit()
    if row is None:
        raise HTTPException(status_code=500, detail="sensor reading could not be saved")
    return {
        "saved": True,
        "table": "sensor_readings",
        "sensor_type": sensor_type,
        "reading_id": row["reading_id"],
        "created_at": normalize_datetime(row["created_at"]),
        "cleanup_deleted_rows": deleted_count,
        "sensor": normalize_response_payload(payload),
        "state": normalize_response_payload(state),
    }
