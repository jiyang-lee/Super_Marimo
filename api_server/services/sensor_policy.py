from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Optional

from extensions.db import get_db_connection
from schemas import RealtimeSensorPayload
from services.sensor_analytics import compute_sensor_metrics
from services.device_event_service import save_device_event
from services.runtime_settings import get_runtime_settings, set_distance_inside_threshold
from services.sensor_judge import judge_realtime_state
from utils import normalize_datetime

logger = logging.getLogger("sensor_policy")


def get_latest_proactive_greeting_at(conn) -> Optional[datetime]:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT created_at
            FROM device_event_log
            WHERE event_type = 'proactive_greeting'
            ORDER BY created_at DESC
            LIMIT 1
            """
        )
        row = cur.fetchone()
    if row is None:
        return None
    return row["created_at"]


def get_latest_sensor_warning_at(conn, device_id: str) -> Optional[datetime]:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT created_at
            FROM device_event_log
            WHERE event_type = 'sensor_warning'
              AND device_id = %s
            ORDER BY created_at DESC
            LIMIT 1
            """,
            (device_id,),
        )
        row = cur.fetchone()
    if row is None:
        return None
    return row["created_at"]


def can_emit_proactive_greeting(conn, *, now: Optional[datetime] = None) -> dict[str, Any]:
    from config import PROACTIVE_GREETING_COOLDOWN_SECONDS

    current_time = now or datetime.now(timezone.utc)
    last_greeting_at = get_latest_proactive_greeting_at(conn)
    if last_greeting_at is None:
        return {"allowed": True, "last_greeting_at": None, "cooldown_remaining_sec": 0}

    elapsed = (current_time - last_greeting_at).total_seconds()
    cooldown_remaining = max(0, PROACTIVE_GREETING_COOLDOWN_SECONDS - int(elapsed))
    return {
        "allowed": elapsed >= PROACTIVE_GREETING_COOLDOWN_SECONDS,
        "last_greeting_at": normalize_datetime(last_greeting_at),
        "cooldown_remaining_sec": cooldown_remaining,
    }


def can_emit_sensor_warning(conn, device_id: str, *, now: Optional[datetime] = None) -> dict[str, Any]:
    from config import SENSOR_WARNING_COOLDOWN_SECONDS

    current_time = now or datetime.now(timezone.utc)
    last_warning_at = get_latest_sensor_warning_at(conn, device_id)
    if last_warning_at is None:
        return {"allowed": True, "last_warning_at": None, "cooldown_remaining_sec": 0}

    elapsed = (current_time - last_warning_at).total_seconds()
    cooldown_remaining = max(0, SENSOR_WARNING_COOLDOWN_SECONDS - int(elapsed))
    return {
        "allowed": elapsed >= SENSOR_WARNING_COOLDOWN_SECONDS,
        "last_warning_at": normalize_datetime(last_warning_at),
        "cooldown_remaining_sec": cooldown_remaining,
    }


def _resolve_greeting_text() -> str:
    from config import (
        LLM_SERVER_URL,
        PROACTIVE_GREETING_LLM_PROMPT,
        PROACTIVE_GREETING_TEXT,
        PROACTIVE_GREETING_USE_LLM,
    )

    if not PROACTIVE_GREETING_USE_LLM:
        from random import choice

        greetings = [
            PROACTIVE_GREETING_TEXT,
            "안녕하세요. 마리모가 먼저 인사드릴게요.",
            "여기에 있어요. 오늘은 어떤 기분이에요?",
            "안녕하세요. 조금 가까이 오셨어요.",
        ]
        return choice([text for text in greetings if text])

    import httpx

    try:
        with httpx.Client(timeout=10.0) as client:
            response = client.post(
                f"{LLM_SERVER_URL}/generate",
                json={
                    "question": PROACTIVE_GREETING_LLM_PROMPT,
                    "history": [],
                    "use_sensor_context": False,
                },
            )
            response.raise_for_status()
            data = response.json()
            answer = str(data.get("answer", "")).strip()
            return answer or PROACTIVE_GREETING_TEXT
    except Exception:
        return PROACTIVE_GREETING_TEXT


def build_realtime_next_action(
    payload: RealtimeSensorPayload,
    *,
    session_id: Optional[str] = None,
    device_id: str = "",
    trigger_source: str = "sensor",
) -> dict[str, Any]:
    from config import PROACTIVE_GREETING_COOLDOWN_SECONDS, SENSOR_WARNING_DISTANCE_THRESHOLD_CM

    settings = get_runtime_settings()
    threshold_cm = float(settings.get("distance_threshold_cm") or SENSOR_WARNING_DISTANCE_THRESHOLD_CM)
    detection_enabled = bool(settings.get("distance_detection_enabled", True))
    was_inside = bool(settings.get("distance_inside_threshold", False))
    is_inside = payload.distance <= threshold_cm

    if not detection_enabled:
        if was_inside:
            set_distance_inside_threshold(False)
        return {
            "type": "none",
            "reason": "distance_detection_disabled",
            "threshold_cm": threshold_cm,
            "distance_cm": payload.distance,
        }

    if not is_inside:
        if was_inside:
            set_distance_inside_threshold(False)
        return {
            "type": "none",
            "reason": "distance_above_threshold",
            "threshold_cm": threshold_cm,
            "distance_cm": payload.distance,
        }

    if was_inside:
        return {
            "type": "none",
            "reason": "distance_already_inside_threshold",
            "threshold_cm": threshold_cm,
            "distance_cm": payload.distance,
        }

    with get_db_connection() as conn:
        metrics = compute_sensor_metrics(conn, current_payload=payload.model_dump(), current_sensor_type="realtime")
        state = judge_realtime_state(payload, metrics=metrics)
        set_distance_inside_threshold(True)

        greeting_policy = can_emit_proactive_greeting(conn)
        warning_policy = can_emit_sensor_warning(conn, device_id)

    warning_meta = {
        "policy": "distance_threshold",
        "threshold_cm": threshold_cm,
        "distance_cm": payload.distance,
        "distance_entry": True,
    }
    if not warning_policy["allowed"]:
        warning_meta["skipped_due_to_cooldown"] = True
        warning_meta["cooldown_remaining_sec"] = warning_policy["cooldown_remaining_sec"]

    warning_event = save_device_event(
        {
            "session_id": session_id,
            "event_type": "sensor_warning",
            "device_id": device_id,
            "trigger_source": trigger_source,
            "distance": payload.distance,
            "sensor": payload.model_dump(),
            "state_level": state["level"],
            "state_alerts": state["alerts"],
            "generated_text": "거리가 가까워졌습니다.",
            "played": False,
            "status": "tts_generated",
            "meta": warning_meta,
        }
    )

    if not greeting_policy["allowed"]:
        return {
            "type": "sensor_warning",
            "threshold_cm": threshold_cm,
            "distance_cm": payload.distance,
            "text": "거리가 가까워졌습니다.",
            "device_event": warning_event["event"] if warning_event else None,
            "cooldown_seconds": PROACTIVE_GREETING_COOLDOWN_SECONDS,
            "cooldown_remaining_sec": greeting_policy["cooldown_remaining_sec"],
        }

    greeting_text = _resolve_greeting_text()

    # Build meta dictionary, including warning_event_id only if warning_event exists
    meta = {
        "policy": "distance_threshold",
        "threshold_cm": threshold_cm,
        "distance_cm": payload.distance,
        "cooldown_seconds": PROACTIVE_GREETING_COOLDOWN_SECONDS,
        "cooldown_ignored_for_distance_entry": True,
    }
    if warning_event:
        meta["warning_event_id"] = warning_event["event"]["event_id"]

    try:
        greeting_event = save_device_event(
            {
                "session_id": session_id,
                "event_type": "proactive_greeting",
                "device_id": device_id,
                "trigger_source": trigger_source,
                "distance": payload.distance,
                "sensor": payload.model_dump(),
                "state_level": state["level"],
                "state_alerts": state["alerts"],
                "generated_text": greeting_text,
                "played": False,
                "status": "pending",
                "meta": meta,
            }
        )
    except Exception as exc:
        logger.error("[proactive_greeting] Failed to create event: %s", exc, exc_info=True)
        raise
    return {
        "type": "proactive_greeting",
        "threshold_cm": threshold_cm,
        "distance_cm": payload.distance,
        "text": greeting_text,
        "device_event": greeting_event["event"],
        "warning_event": warning_event["event"] if warning_event else None,
        "cooldown_seconds": PROACTIVE_GREETING_COOLDOWN_SECONDS,
    }
