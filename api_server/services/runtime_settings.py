from typing import Any

from psycopg.types.json import Json

from config import SENSOR_WARNING_DISTANCE_THRESHOLD_CM
from extensions.db import get_db_connection
from utils import normalize_response_payload


RUNTIME_SETTINGS_KEY = "sensor_runtime"

DEFAULT_RUNTIME_SETTINGS: dict[str, Any] = {
    "distance_detection_enabled": True,
    "wake_enabled": True,
    "web_voice_enabled": False,
    "distance_threshold_cm": SENSOR_WARNING_DISTANCE_THRESHOLD_CM,
    "distance_inside_threshold": False,
}


def _normalize_settings(value: dict[str, Any] | None) -> dict[str, Any]:
    merged = {**DEFAULT_RUNTIME_SETTINGS, **(value or {})}
    merged["distance_detection_enabled"] = bool(merged.get("distance_detection_enabled"))
    merged["wake_enabled"] = bool(merged.get("wake_enabled"))
    merged["web_voice_enabled"] = bool(merged.get("web_voice_enabled"))
    merged["distance_inside_threshold"] = bool(merged.get("distance_inside_threshold"))
    merged["distance_threshold_cm"] = float(merged.get("distance_threshold_cm") or SENSOR_WARNING_DISTANCE_THRESHOLD_CM)
    return merged


def get_runtime_settings() -> dict[str, Any]:
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT setting_value, updated_at
                FROM runtime_settings
                WHERE setting_key = %s
                """,
                (RUNTIME_SETTINGS_KEY,),
            )
            row = cur.fetchone()
    settings = _normalize_settings(row["setting_value"] if row else None)
    if row:
        settings["updated_at"] = row["updated_at"]
    return normalize_response_payload(settings)


def update_runtime_settings(patch: dict[str, Any]) -> dict[str, Any]:
    current = get_runtime_settings()
    allowed_keys = {
        "distance_detection_enabled",
        "wake_enabled",
        "web_voice_enabled",
        "distance_threshold_cm",
        "distance_inside_threshold",
    }
    next_settings = {
        key: value
        for key, value in current.items()
        if key in allowed_keys
    }
    for key, value in patch.items():
        if key in allowed_keys:
            next_settings[key] = value
    if next_settings.get("distance_detection_enabled") is False:
        next_settings["distance_inside_threshold"] = False
    next_settings = _normalize_settings(next_settings)

    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO runtime_settings (setting_key, setting_value, updated_at)
                VALUES (%s, %s, NOW())
                ON CONFLICT (setting_key)
                DO UPDATE SET setting_value = EXCLUDED.setting_value, updated_at = NOW()
                RETURNING setting_value, updated_at
                """,
                (RUNTIME_SETTINGS_KEY, Json(next_settings)),
            )
            row = cur.fetchone()
        conn.commit()

    saved = _normalize_settings(row["setting_value"] if row else next_settings)
    if row:
        saved["updated_at"] = row["updated_at"]
    return normalize_response_payload(saved)


def set_distance_inside_threshold(inside: bool) -> dict[str, Any]:
    return update_runtime_settings({"distance_inside_threshold": inside})
