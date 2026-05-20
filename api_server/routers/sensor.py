from typing import Any

from fastapi import APIRouter

from extensions.db import get_db_connection
from schemas import HourlySensorPayload, RealtimeSensorPayload, RuntimeSettingsPayload, SensorPayload
from services.sensor_judge import judge_hourly_state, judge_realtime_state, judge_sensor_state
from services.sensor_policy import build_realtime_next_action
from services.sensor_store import (
    expand_sensor_row,
    get_recent_light_raw_samples,
    get_latest_sensor_row,
    get_recent_sensor_rows,
    get_recent_water_raw_samples,
    save_light_raw_sample,
    save_sensor_reading,
    save_water_raw_sample,
)
from services.sensor_utils import build_merged_payload
from services.runtime_settings import get_runtime_settings, update_runtime_settings
from utils import normalize_response_payload

router = APIRouter()


@router.post("/sensor/status")
def sensor_status(payload: SensorPayload) -> dict[str, Any]:
    return {"sensor": payload.model_dump(), "state": judge_sensor_state(payload)}


@router.post("/sensor/ingest")
def sensor_ingest(payload: RealtimeSensorPayload) -> dict[str, Any]:
    state = judge_realtime_state(payload)
    response = save_sensor_reading(payload.model_dump(), "realtime", state)
    response["next_action"] = build_realtime_next_action(payload)
    return response


@router.post("/sensor/realtime-ingest")
def sensor_realtime_ingest(payload: RealtimeSensorPayload) -> dict[str, Any]:
    state = judge_realtime_state(payload)
    response = save_sensor_reading(payload.model_dump(), "realtime", state)
    if payload.light_raw is not None:
        response["light_raw_sample"] = save_light_raw_sample(payload.light_raw)
    if payload.water_raw is not None:
        response["water_raw_sample"] = save_water_raw_sample(payload.water_raw)
    response["next_action"] = build_realtime_next_action(payload)
    return response


@router.post("/sensor/hourly-ingest")
def sensor_hourly_ingest(payload: HourlySensorPayload) -> dict[str, Any]:
    state = judge_hourly_state(payload)
    response = save_sensor_reading(payload.model_dump(), "hourly", state)
    if payload.water_raw is not None:
        response["water_raw_sample"] = save_water_raw_sample(payload.water_raw)
    if payload.light_raw is not None:
        response["light_raw_sample"] = save_light_raw_sample(payload.light_raw)
    return response


@router.get("/sensor/latest")
def sensor_latest() -> dict[str, Any]:
    with get_db_connection() as conn:
        realtime_row = get_latest_sensor_row(conn, "realtime")
        hourly_row = get_latest_sensor_row(conn, "hourly")

    merged = build_merged_payload(realtime_row, hourly_row)
    runtime_settings = get_runtime_settings()
    latest_distance = (merged or {}).get("distance") if merged else None
    threshold = float(runtime_settings.get("distance_threshold_cm") or 50)
    return {
        "latest_realtime": normalize_response_payload(expand_sensor_row(realtime_row)),
        "latest_hourly": normalize_response_payload(expand_sensor_row(hourly_row)),
        "latest_merged": normalize_response_payload(merged),
        "runtime_settings": runtime_settings,
        "distance_inside_threshold": bool(latest_distance is not None and latest_distance <= threshold),
    }


@router.get("/sensor/history")
def sensor_history(limit: int = 24) -> dict[str, Any]:
    safe_limit = max(1, min(limit, 120))
    with get_db_connection() as conn:
        realtime_rows = get_recent_sensor_rows(conn, "realtime", safe_limit)
        hourly_rows = get_recent_sensor_rows(conn, "hourly", safe_limit)
        realtime_row = get_latest_sensor_row(conn, "realtime")
        hourly_row = get_latest_sensor_row(conn, "hourly")

    merged = build_merged_payload(realtime_row, hourly_row)
    runtime_settings = get_runtime_settings()
    latest_distance = (merged or {}).get("distance") if merged else None
    threshold = float(runtime_settings.get("distance_threshold_cm") or 50)
    return {
        "limit": safe_limit,
        "latest_realtime": normalize_response_payload(expand_sensor_row(realtime_row)),
        "latest_hourly": normalize_response_payload(expand_sensor_row(hourly_row)),
        "latest_merged": normalize_response_payload(merged),
        "runtime_settings": runtime_settings,
        "distance_inside_threshold": bool(latest_distance is not None and latest_distance <= threshold),
        "realtime_history": normalize_response_payload(realtime_rows),
        "hourly_history": normalize_response_payload(hourly_rows),
    }


@router.get("/sensor/water-raw-samples")
def sensor_water_raw_samples(limit: int = 144) -> dict[str, Any]:
    safe_limit = max(1, min(limit, 1000))
    return {
        "limit": safe_limit,
        "samples": normalize_response_payload(get_recent_water_raw_samples(safe_limit)),
    }


@router.get("/sensor/light-raw-samples")
def sensor_light_raw_samples(limit: int = 144) -> dict[str, Any]:
    safe_limit = max(1, min(limit, 1000))
    return {
        "limit": safe_limit,
        "samples": normalize_response_payload(get_recent_light_raw_samples(safe_limit)),
    }


@router.get("/sensor/runtime-settings")
def sensor_runtime_settings() -> dict[str, Any]:
    return {"settings": get_runtime_settings()}


@router.put("/sensor/runtime-settings")
def sensor_runtime_settings_update(payload: RuntimeSettingsPayload) -> dict[str, Any]:
    patch = payload.model_dump(exclude_none=True)
    return {"settings": update_runtime_settings(patch)}
