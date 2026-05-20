from typing import Any

from psycopg.types.json import Json

from config import SENSOR_WARNING_DISTANCE_THRESHOLD_CM
from extensions.db import get_db_connection
from utils import normalize_response_payload


RUNTIME_SETTINGS_KEY = "sensor_runtime"

DEFAULT_RUNTIME_SETTINGS: dict[str, Any] = {
    "distance_detection_enabled": False,
    "wake_enabled": False,
    "web_voice_enabled": True,
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


def _get_runtime_settings_raw(conn) -> dict[str, Any]:
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


def get_runtime_settings(conn=None) -> dict[str, Any]:
    if conn is not None:
        return _get_runtime_settings_raw(conn)
    with get_db_connection() as conn:
        return _get_runtime_settings_raw(conn)


def update_runtime_settings(patch: dict[str, Any], conn=None) -> dict[str, Any]:
    current = get_runtime_settings(conn=conn)
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
            # web_voice_enabled 모드 전환 시 거리 감지 및 호출어 자동 강제 동기화 가드
            if key == "web_voice_enabled":
                if value is True:
                    next_settings["distance_detection_enabled"] = False
                    next_settings["wake_enabled"] = False
                else:
                    next_settings["distance_detection_enabled"] = True
                    next_settings["wake_enabled"] = True

    if next_settings.get("distance_detection_enabled") is False:
        next_settings["distance_inside_threshold"] = False
    next_settings = _normalize_settings(next_settings)

    if conn is not None:
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
        saved = _normalize_settings(row["setting_value"] if row else next_settings)
        if row:
            saved["updated_at"] = row["updated_at"]
        return normalize_response_payload(saved)

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


def save_runtime_settings_history(
    conn,
    *,
    setting_key: str,
    previous_value: dict[str, Any] | None,
    new_value: dict[str, Any],
    changed_by: str | None = None,
    action_type: str | None = None,
    summary: str | None = None,
) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO runtime_settings_history (
                setting_key, previous_value, new_value, changed_by, action_type, summary
            )
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (
                setting_key,
                Json(previous_value) if previous_value is not None else None,
                Json(new_value),
                changed_by,
                action_type,
                summary,
            ),
        )


def set_distance_inside_threshold(inside: bool, conn=None) -> dict[str, Any]:
    return update_runtime_settings({"distance_inside_threshold": inside}, conn=conn)
