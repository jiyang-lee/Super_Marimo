from datetime import datetime, timezone
from typing import Any, Optional

from extensions.db import get_db_connection
from schemas import RealtimeSensorPayload
from services.device_event_service import save_device_event
from services.sensor_judge import judge_realtime_state
from services.sensor_store import get_latest_sensor_row
from utils import normalize_datetime


def get_latest_proactive_greeting_at(conn) -> Optional[datetime]:
    from config import PROACTIVE_GREETING_COOLDOWN_SECONDS

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


def _resolve_greeting_text() -> str:
    from config import (
        LLM_SERVER_URL,
        PROACTIVE_GREETING_LLM_PROMPT,
        PROACTIVE_GREETING_TEXT,
        PROACTIVE_GREETING_USE_LLM,
    )

    if not PROACTIVE_GREETING_USE_LLM:
        return PROACTIVE_GREETING_TEXT

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
    from config import (
        PROACTIVE_GREETING_COOLDOWN_SECONDS,
        PROACTIVE_GREETING_TEXT,
        SENSOR_WARNING_DISTANCE_THRESHOLD_CM,
    )

    state = judge_realtime_state(payload)
    if payload.distance > SENSOR_WARNING_DISTANCE_THRESHOLD_CM:
        return {
            "type": "none",
            "reason": "distance_above_threshold",
            "threshold_cm": SENSOR_WARNING_DISTANCE_THRESHOLD_CM,
            "distance_cm": payload.distance,
        }

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
            "generated_text": f"distance={payload.distance}cm threshold={SENSOR_WARNING_DISTANCE_THRESHOLD_CM}cm",
            "played": False,
            "meta": {
                "policy": "distance_threshold",
                "threshold_cm": SENSOR_WARNING_DISTANCE_THRESHOLD_CM,
                "distance_cm": payload.distance,
            },
        }
    )

    with get_db_connection() as conn:
        greeting_policy = can_emit_proactive_greeting(conn)

    if not greeting_policy["allowed"]:
        return {
            "type": "sensor_warning",
            "threshold_cm": SENSOR_WARNING_DISTANCE_THRESHOLD_CM,
            "distance_cm": payload.distance,
            "device_event": warning_event["event"],
            "cooldown_remaining_sec": greeting_policy["cooldown_remaining_sec"],
            "last_greeting_at": greeting_policy["last_greeting_at"],
        }

    greeting_text = _resolve_greeting_text()

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
            "meta": {
                "policy": "distance_threshold",
                "threshold_cm": SENSOR_WARNING_DISTANCE_THRESHOLD_CM,
                "distance_cm": payload.distance,
                "cooldown_seconds": PROACTIVE_GREETING_COOLDOWN_SECONDS,
                "warning_event_id": warning_event["event"]["event_id"],
            },
        }
    )
    return {
        "type": "proactive_greeting",
        "threshold_cm": SENSOR_WARNING_DISTANCE_THRESHOLD_CM,
        "distance_cm": payload.distance,
        "text": greeting_text,
        "device_event": greeting_event["event"],
        "warning_event": warning_event["event"],
        "cooldown_seconds": PROACTIVE_GREETING_COOLDOWN_SECONDS,
    }
