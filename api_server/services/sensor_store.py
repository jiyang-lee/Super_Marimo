from typing import Any, Optional

from fastapi import HTTPException
from psycopg.types.json import Json

from extensions.db import cleanup_old_realtime_rows, get_db_connection
from schemas import SensorPayload
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


def get_recent_water_raw_samples(limit: int = 144) -> list[dict[str, Any]]:
    safe_limit = max(1, min(limit, 1000))
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT sample_id, created_at, raw_value
                FROM water_raw_samples
                ORDER BY created_at DESC
                LIMIT %s
                """,
                (safe_limit,),
            )
            rows = cur.fetchall() or []

    samples: list[dict[str, Any]] = []
    for row in reversed(rows):
        samples.append(
            {
                "sample_id": row["sample_id"],
                "created_at": normalize_datetime(row["created_at"]),
                "raw_value": row["raw_value"],
            }
        )
    return samples


def get_recent_light_raw_samples(limit: int = 144) -> list[dict[str, Any]]:
    safe_limit = max(1, min(limit, 1000))
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT sample_id, created_at, raw_value
                FROM light_raw_samples
                ORDER BY created_at DESC
                LIMIT %s
                """,
                (safe_limit,),
            )
            rows = cur.fetchall() or []

    samples: list[dict[str, Any]] = []
    for row in reversed(rows):
        samples.append(
            {
                "sample_id": row["sample_id"],
                "created_at": normalize_datetime(row["created_at"]),
                "raw_value": row["raw_value"],
            }
        )
    return samples


def load_latest_sensor_payload() -> SensorPayload:
    fallback = default_sensor_payload().model_dump()
    try:
        with get_db_connection() as conn:
            hourly_row = get_latest_sensor_row(conn, "hourly")
            realtime_row = get_latest_sensor_row(conn, "realtime")
    except Exception:
        return default_sensor_payload()

    hourly_payload = extract_payload(hourly_row)
    realtime_payload = extract_payload(realtime_row)

    if hourly_payload:
        fallback["temperature"] = hourly_payload.get("temperature", fallback["temperature"])
        fallback["humidity"] = hourly_payload.get("humidity", fallback["humidity"])
        fallback["water_level"] = hourly_payload.get("water_level", fallback["water_level"])
    if realtime_payload:
        fallback["light"] = realtime_payload.get("light", fallback["light"])
        fallback["distance"] = realtime_payload.get("distance", fallback["distance"])

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


def save_water_raw_sample(raw_value: int) -> dict[str, Any]:
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO water_raw_samples (raw_value)
                VALUES (%s)
                RETURNING sample_id, created_at, raw_value
                """,
                (raw_value,),
            )
            row = cur.fetchone()
        conn.commit()
    if row is None:
        raise HTTPException(status_code=500, detail="water raw sample could not be saved")
    return {
        "saved": True,
        "table": "water_raw_samples",
        "sample_id": row["sample_id"],
        "created_at": normalize_datetime(row["created_at"]),
        "raw_value": row["raw_value"],
    }


def save_light_raw_sample(raw_value: int) -> dict[str, Any]:
    from datetime import datetime, timezone
    from config import LIGHT_RAW_SAMPLE_INTERVAL_SECONDS

    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT MAX(created_at) as last_at
                FROM light_raw_samples
                """,
                (),
            )
            last_row = cur.fetchone()

    now = datetime.now(timezone.utc)
    last_at = last_row["last_at"] if last_row else None
    if last_at is not None:
        elapsed = (now - last_at).total_seconds()
        if elapsed < LIGHT_RAW_SAMPLE_INTERVAL_SECONDS:
            return {
                "saved": False,
                "skipped": True,
                "reason": "rate_limit",
                "cooldown_remaining_sec": int(LIGHT_RAW_SAMPLE_INTERVAL_SECONDS - elapsed),
                "last_saved_at": normalize_datetime(last_at),
                "raw_value": raw_value,
            }

    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO light_raw_samples (raw_value)
                VALUES (%s)
                RETURNING sample_id, created_at, raw_value
                """,
                (raw_value,),
            )
            row = cur.fetchone()
        conn.commit()
    if row is None:
        raise HTTPException(status_code=500, detail="light raw sample could not be saved")
    return {
        "saved": True,
        "table": "light_raw_samples",
        "sample_id": row["sample_id"],
        "created_at": normalize_datetime(row["created_at"]),
        "raw_value": row["raw_value"],
    }
