from __future__ import annotations

import json
import re
import unicodedata
from typing import Any, Optional
from uuid import UUID, uuid4

import httpx
from fastapi import HTTPException
from psycopg.types.json import Json

from config import LLM_SERVER_URL
from extensions.db import get_db_connection
from schemas import SensorPayload
from services.device_event_service import save_device_event
from services.llm_action_contract import compose_final_answer, normalize_llm_action_proposal
from services.runtime_action_service import apply_runtime_action, resolve_runtime_action
from services.runtime_settings import RUNTIME_SETTINGS_KEY, get_runtime_settings, save_runtime_settings_history
from services.sensor_judge import judge_sensor_state
from services.sensor_store import load_latest_sensor_payload
from services.session_kind import infer_session_kind
from services.session_lifecycle import ensure_session, update_session_meta, update_session_turn
from services.session_message import fetch_recent_session_messages, save_session_message
from utils import normalize_datetime, normalize_response_payload


DEFAULT_PERSONA_MEMO = (
    "마리모는 Super Marimo의 조용한 안내자다. "
    "과장하지 않고, 현재 상태를 짧고 분명하게 설명한다."
)


def _sanitize_llm_sensor_payload(sensor: Optional[SensorPayload]) -> Optional[dict[str, Any]]:
    if sensor is None:
        return None
    sensor_data = sensor.model_dump()
    if sensor_data.get("water_level_normalized_0_100") is not None or sensor_data.get("water_level_recent_avg_2h") is not None:
        sensor_data.pop("water_level", None)
    if sensor_data.get("light_normalized_0_100") is not None or sensor_data.get("light_daytime_avg_13_18") is not None:
        sensor_data.pop("light", None)
    return sensor_data


def sanitize_tts_text(text: str) -> str:
    cleaned = unicodedata.normalize("NFKC", text or "").strip()
    if not cleaned:
        return ""

    cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", cleaned, flags=re.IGNORECASE | re.DOTALL).strip()
    json_start = cleaned.find("{")
    json_end = cleaned.rfind("}")
    if json_start != -1:
        json_blob = cleaned[json_start : json_end + 1] if json_end > json_start else cleaned[json_start:]
        try:
            parsed = json.loads(json_blob)
        except json.JSONDecodeError:
            parsed = None
        if isinstance(parsed, dict):
            for key in ("answer", "tts_text", "llm_answer", "response", "text", "content"):
                value = parsed.get(key)
                if isinstance(value, str) and value.strip():
                    cleaned = value.strip()
                    break
            else:
                for key in ("answer", "tts_text", "llm_answer", "response", "text", "content"):
                    value = parsed.get(key)
                    if value not in (None, ""):
                        cleaned = str(value).strip()
                        break

    cleaned = re.sub(r"[\u200b-\u200d\ufeff\ufe0e\ufe0f]", "", cleaned)
    cleaned = re.sub(r"[\x00-\x1f\x7f]", " ", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned.strip()


def build_session_summary(history: list[dict[str, str]]) -> str:
    if not history:
        return "최근 세션 요약 없음"

    recent = history[-6:]
    parts: list[str] = []
    for item in recent:
        role = (item.get("role") or "").strip().lower()
        content = (item.get("content") or "").strip()
        if not content:
            continue
        label = "사용자" if role == "user" else "어시스턴트" if role == "assistant" else "시스템"
        parts.append(f"{label}: {content[:120]}")
    return " / ".join(parts) if parts else "최근 세션 요약 없음"


async def request_llm(
    question: str,
    sensor: Optional[SensorPayload],
    state: Optional[dict[str, Any]],
    runtime_settings: Optional[dict[str, Any]],
    use_sensor_context: bool,
    history: Optional[list[dict[str, str]]] = None,
    session_summary: Optional[str] = None,
    action_result: Optional[dict[str, Any]] = None,
    persona_memo: Optional[str] = None,
    system_memo: Optional[str] = None,
) -> dict[str, Any]:
    resolved_persona_memo = (persona_memo or DEFAULT_PERSONA_MEMO).strip()
    resolved_system_memo = system_memo.strip() if system_memo else None
    request_body = {
        "question": question,
        "sensor": _sanitize_llm_sensor_payload(sensor),
        "state": state,
        "runtime_settings": runtime_settings,
        "history": history or [],
        "session_summary": session_summary,
        "action_result": action_result,
        "use_sensor_context": use_sensor_context,
        "persona_memo": resolved_persona_memo,
        "system_memo": resolved_system_memo,
    }
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(f"{LLM_SERVER_URL}/generate", json=request_body)
            response.raise_for_status()
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"LLM server error: {exc}") from exc
    return response.json()


async def handle_interaction(
    *,
    session_id: Optional[UUID],
    session_kind: Optional[str] = None,
    text: str,
    sensor: Optional[SensorPayload],
    use_sensor_context: bool,
    source: str,
    persona_memo: Optional[str] = None,
    system_memo: Optional[str] = None,
    is_test: bool = False,
) -> dict[str, Any]:
    resolved_session_id = session_id or uuid4()
    resolved_session_kind = infer_session_kind(session_kind=session_kind, source=source)
    active_sensor: Optional[SensorPayload] = sensor
    state: dict[str, Any] = {"level": "chat", "alerts": []}
    runtime_settings = get_runtime_settings()
    resolved_persona_memo = (persona_memo or DEFAULT_PERSONA_MEMO).strip()
    resolved_system_memo = system_memo.strip() if system_memo else None
    session_summary = "최근 세션 요약 없음"
    action_result: Optional[dict[str, Any]] = None

    if use_sensor_context:
        active_sensor = active_sensor or load_latest_sensor_payload()
        if active_sensor is not None:
            latest_sensor = load_latest_sensor_payload()
            active_sensor_data = active_sensor.model_dump()
            latest_sensor_data = latest_sensor.model_dump()
            for key in (
                "water_level_recent_avg_2h",
                "water_level_normalized_0_100",
                "water_level_sample_count",
                "light_daytime_avg_13_18",
                "light_normalized_0_100",
                "light_daytime_sample_count",
                "light_daytime_window_label",
                "sensor_semantics",
                "sensor_summary",
            ):
                if active_sensor_data.get(key) is None and latest_sensor_data.get(key) is not None:
                    active_sensor_data[key] = latest_sensor_data[key]
            active_sensor = SensorPayload(**active_sensor_data)
        state = judge_sensor_state(active_sensor)

    with get_db_connection() as conn:
        session_row, session_created = ensure_session(conn, resolved_session_id, resolved_session_kind)
        if is_test:
            session_row = update_session_meta(conn, resolved_session_id, {"is_test": True})
        history = fetch_recent_session_messages(conn, resolved_session_id)
        session_summary = build_session_summary(history)

        save_session_message(
            conn,
            resolved_session_id,
            "user",
            text,
            meta={
                "source": source,
                "session_kind": resolved_session_kind,
                "use_sensor_context": use_sensor_context,
                "session_summary": session_summary,
            },
        )

        if source in ("voice", "voice_agent"):
            save_device_event(
                {
                    "session_id": str(resolved_session_id),
                    "event_type": "stt_completed",
                    "device_id": "default",
                    "trigger_source": source,
                    "distance": None,
                    "sensor": active_sensor.model_dump() if active_sensor else None,
                    "state_level": state["level"],
                    "state_alerts": state.get("alerts", []),
                    "generated_text": text,
                    "played": False,
                    "status": "pending",
                    "meta": {
                        "source": source,
                        "session_kind": resolved_session_kind,
                        "session_created": session_created,
                        "session_summary": session_summary,
                        "use_sensor_context": use_sensor_context,
                    },
                }
            )

        llm = await request_llm(
            text,
            active_sensor,
            state,
            runtime_settings,
            use_sensor_context=use_sensor_context,
            history=history,
            session_summary=session_summary,
            action_result=action_result,
            persona_memo=resolved_persona_memo,
            system_memo=resolved_system_memo,
        )
        raw_answer = str(llm.get("answer", "")).strip()
        answer = sanitize_tts_text(raw_answer) or raw_answer
        if not answer:
            if source in ("voice", "voice_agent"):
                save_device_event(
                    {
                        "session_id": str(resolved_session_id),
                        "event_type": "llm_completed",
                        "device_id": "default",
                        "trigger_source": source,
                        "distance": None,
                        "sensor": active_sensor.model_dump() if active_sensor else None,
                        "state_level": state["level"],
                        "state_alerts": state.get("alerts", []),
                        "generated_text": "",
                        "played": False,
                        "status": "failed",
                        "meta": {
                            "source": source,
                            "session_kind": resolved_session_kind,
                            "error": "LLM response has no answer",
                            "session_summary": session_summary,
                        },
                    }
                )
            raise HTTPException(status_code=502, detail="LLM response has no answer")

        action_request = normalize_llm_action_proposal(llm.get("action_proposal"))
        if action_request is None:
            action_request = resolve_runtime_action(
                text,
                runtime_settings=runtime_settings,
            )

        if action_request is not None:
            action_request["before"] = runtime_settings
            action_result = apply_runtime_action(action_request, conn=conn)
            runtime_settings = get_runtime_settings(conn=conn)
            answer = compose_final_answer(answer, action_result)
            llm["action_result"] = action_result
            llm["final_answer"] = answer
            llm["executed_action"] = action_request
            save_runtime_settings_history(
                conn,
                setting_key=RUNTIME_SETTINGS_KEY,
                previous_value=action_request.get("before"),
                new_value=runtime_settings,
                changed_by=str(resolved_session_id),
                action_type=action_result.get("action_type"),
                summary=action_result.get("summary"),
            )
            session_row = update_session_meta(
                conn,
                resolved_session_id,
                {
                    "last_agent_action": action_result,
                    "last_sensor_summary": {
                        "sensor": normalize_response_payload(active_sensor.model_dump() if active_sensor is not None else None),
                        "state": normalize_response_payload(state),
                        "runtime_settings": normalize_response_payload(runtime_settings),
                    },
                    "last_llm_contract": normalize_response_payload(llm),
                },
            )
        else:
            llm["final_answer"] = answer

        tts_text = sanitize_tts_text(answer) or answer

        save_session_message(
            conn,
            resolved_session_id,
            "assistant",
            answer,
            meta={
                "source": source,
                "session_kind": resolved_session_kind,
                "session_summary": session_summary,
                "action_result": action_result,
                "tts_text": tts_text,
            },
        )

        if source in ("voice", "voice_agent"):
            save_device_event(
                {
                    "session_id": str(resolved_session_id),
                    "event_type": "llm_completed",
                    "device_id": "default",
                    "trigger_source": source,
                    "distance": None,
                    "sensor": active_sensor.model_dump() if active_sensor else None,
                    "state_level": state["level"],
                    "state_alerts": state.get("alerts", []),
                    "generated_text": answer,
                    "played": False,
                    "status": "pending",
                    "meta": {
                        "source": source,
                        "session_kind": resolved_session_kind,
                        "session_summary": session_summary,
                        "action_result": action_result,
                        "runtime_settings": runtime_settings,
                        "tts_text": tts_text,
                    },
                }
            )

        interaction_payload = active_sensor.model_dump() if active_sensor is not None else {}
        alerts = state.get("alerts") or []
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO interaction_log (
                    session_id, stt_text, llm_answer, tts_text, sensor_json, state_level, state_alerts, meta
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING interaction_id, created_at
                """,
                (
                    resolved_session_id,
                    text,
                    answer,
                    tts_text,
                    Json(interaction_payload),
                    state["level"],
                    Json(alerts),
                    Json(
                        {
                            "source": source,
                            "session_kind": resolved_session_kind,
                            "session_created": session_created,
                            "session_summary": session_summary,
                            "action_result": action_result,
                            "runtime_settings": runtime_settings,
                            "tts_text": tts_text,
                        }
                    ),
                ),
            )
            interaction_row = cur.fetchone()

        if interaction_row is None:
            raise HTTPException(status_code=500, detail="interaction log could not be saved")

        session_row = update_session_turn(conn, resolved_session_id)
        conn.commit()

    return {
        "saved": True,
        "session_id": str(resolved_session_id),
        "session_created": session_created,
        "interaction_id": interaction_row["interaction_id"],
        "created_at": normalize_datetime(interaction_row["created_at"]),
        "messages_saved": 2,
        "history_count": len(history),
        "stt_text": text,
        "llm_answer": answer,
        "tts_text": tts_text,
        "use_sensor_context": use_sensor_context,
        "runtime_settings": normalize_response_payload(runtime_settings),
        "session_summary": session_summary,
        "action_result": normalize_response_payload(action_result),
        "sensor": normalize_response_payload(active_sensor.model_dump() if active_sensor is not None else None),
        "state": normalize_response_payload(state),
        "llm": normalize_response_payload(llm),
        "session": normalize_response_payload(session_row),
    }
