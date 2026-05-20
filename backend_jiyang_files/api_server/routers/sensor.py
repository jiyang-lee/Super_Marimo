from typing import Any

from fastapi import APIRouter

from extensions.db import get_db_connection
from schemas import HourlySensorPayload, RealtimeSensorPayload, RuntimeSettingsPayload, SensorPayload
from services.sensor_judge import judge_hourly_state, judge_realtime_state, judge_sensor_state
from services.sensor_policy import build_realtime_next_action
from services.sensor_store import (
    expand_sensor_row,
    get_latest_sensor_row,
    get_recent_sensor_rows,
    save_sensor_reading,
)
from services.sensor_utils import build_merged_payload
from services.runtime_settings import get_runtime_settings, update_runtime_settings
from utils import normalize_response_payload

router = APIRouter()


def _safe_build_realtime_next_action(payload: RealtimeSensorPayload) -> dict[str, Any]:
    try:
        return build_realtime_next_action(payload)
    except Exception as exc:
        return {
            "type": "error",
            "reason": "next_action_failed",
            "error": str(exc),
        }


@router.post("/sensor/status")
def sensor_status(payload: SensorPayload) -> dict[str, Any]:
    return {"sensor": payload.model_dump(), "state": judge_sensor_state(payload)}


@router.post("/sensor/ingest")
def sensor_ingest(payload: RealtimeSensorPayload) -> dict[str, Any]:
    state = judge_realtime_state(payload)
    response = save_sensor_reading(payload.model_dump(), "realtime", state)
    response["next_action"] = _safe_build_realtime_next_action(payload)
    return response


@router.post("/sensor/realtime-ingest")
def sensor_realtime_ingest(payload: RealtimeSensorPayload) -> dict[str, Any]:
    state = judge_realtime_state(payload)
    response = save_sensor_reading(payload.model_dump(), "realtime", state)
    response["next_action"] = _safe_build_realtime_next_action(payload)
    return response


@router.post("/sensor/hourly-ingest")
def sensor_hourly_ingest(payload: HourlySensorPayload) -> dict[str, Any]:
    state = judge_hourly_state(payload)
    response = save_sensor_reading(payload.model_dump(), "hourly", state)
    return response


@router.get("/sensor/latest")
def sensor_latest() -> dict[str, Any]:
    with get_db_connection() as conn:
        realtime_row = get_latest_sensor_row(conn, "realtime")

    merged = build_merged_payload(realtime_row, None)
    runtime_settings = get_runtime_settings()
    latest_distance = (merged or {}).get("distance") if merged else None
    threshold = float(runtime_settings.get("distance_threshold_cm") or 50)
    return {
        "latest_realtime": normalize_response_payload(expand_sensor_row(realtime_row)),
        "latest_hourly": None,
        "latest_merged": normalize_response_payload(merged),
        "runtime_settings": runtime_settings,
        "distance_inside_threshold": bool(latest_distance is not None and latest_distance <= threshold),
    }


@router.get("/sensor/history")
def sensor_history(limit: int = 24) -> dict[str, Any]:
    safe_limit = max(1, min(limit, 120))
    with get_db_connection() as conn:
        realtime_rows = get_recent_sensor_rows(conn, "realtime", safe_limit)
        realtime_row = get_latest_sensor_row(conn, "realtime")

    merged = build_merged_payload(realtime_row, None)
    runtime_settings = get_runtime_settings()
    latest_distance = (merged or {}).get("distance") if merged else None
    threshold = float(runtime_settings.get("distance_threshold_cm") or 50)
    return {
        "limit": safe_limit,
        "latest_realtime": normalize_response_payload(expand_sensor_row(realtime_row)),
        "latest_hourly": None,
        "latest_merged": normalize_response_payload(merged),
        "runtime_settings": runtime_settings,
        "distance_inside_threshold": bool(latest_distance is not None and latest_distance <= threshold),
        "realtime_history": normalize_response_payload(realtime_rows),
        "hourly_history": [],
    }


@router.get("/sensor/runtime-settings")
def sensor_runtime_settings() -> dict[str, Any]:
    return {"settings": get_runtime_settings()}


@router.put("/sensor/runtime-settings")
def sensor_runtime_settings_update(payload: RuntimeSettingsPayload) -> dict[str, Any]:
    patch = payload.model_dump(exclude_none=True)
    return {"settings": update_runtime_settings(patch)}


@router.get("/sensor/runtime-settings/history")
def sensor_runtime_settings_history(limit: int = 20, setting_key: str | None = None) -> dict[str, Any]:
    safe_limit = max(1, min(limit, 100))
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            if setting_key:
                cur.execute(
                    """
                    SELECT history_id, setting_key, previous_value, new_value, changed_by, changed_at, action_type, summary
                    FROM runtime_settings_history
                    WHERE setting_key = %s
                    ORDER BY changed_at DESC
                    LIMIT %s
                    """,
                    (setting_key, safe_limit),
                )
            else:
                cur.execute(
                    """
                    SELECT history_id, setting_key, previous_value, new_value, changed_by, changed_at, action_type, summary
                    FROM runtime_settings_history
                    ORDER BY changed_at DESC
                    LIMIT %s
                    """,
                    (safe_limit,),
                )
            rows = cur.fetchall()
    return {"history": normalize_response_payload(rows), "limit": safe_limit}
