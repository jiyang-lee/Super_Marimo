from __future__ import annotations

from typing import Any

from pydantic import BaseModel


DEFAULT_PERSONA_MEMO = (
    "너는 Super Marimo의 대화형 응답자다. "
    "한국어로 자연스럽고 짧게 답하되, 필요하면 2~4문장까지 허용한다."
)

ALLOWED_RUNTIME_KEYS = (
    "wake_enabled",
    "distance_detection_enabled",
    "distance_threshold_cm",
    "web_voice_enabled",
)

MAX_HISTORY_MESSAGES = 8


def _to_plain(value: Any) -> Any:
    if isinstance(value, BaseModel):
        return value.model_dump()
    if hasattr(value, "model_dump"):
        return value.model_dump()
    return value


def _format_block(label: str, value: Any) -> str:
    plain = _to_plain(value)
    if plain in (None, "", {}, []):
        return f"{label}: 없음"
    return f"{label}: {plain}"


def _build_distance_context(payload: Any) -> str:
    if not bool(getattr(payload, "use_sensor_context", False)):
        return ""

    sensor = _to_plain(getattr(payload, "sensor", None)) or {}
    runtime_settings = _to_plain(getattr(payload, "runtime_settings", None)) or {}
    distance = sensor.get("distance")
    if distance is None:
        return ""

    parts = ["distance_context: 거리 관련 질문이면 이 정보를 참고한다."]
    try:
        parts.append(f"distance_context: 현재 거리 {float(distance):.1f}cm")
    except (TypeError, ValueError):
        pass

    threshold = runtime_settings.get("distance_threshold_cm")
    if threshold is not None:
        try:
            parts.append(f"distance_context: 기준 {float(threshold):.0f}cm")
        except (TypeError, ValueError):
            pass

    inside = runtime_settings.get("distance_inside_threshold")
    if inside is not None:
        parts.append("distance_context: 현재는 기준 안쪽이다." if inside else "distance_context: 현재는 기준 바깥쪽이다.")

    return "\n".join(parts)


def format_context(payload: Any) -> str:
    use_sensor_context = bool(getattr(payload, "use_sensor_context", False))
    sensor = _to_plain(getattr(payload, "sensor", None)) or {}
    state = _to_plain(getattr(payload, "state", None)) or {}
    runtime_settings = _to_plain(getattr(payload, "runtime_settings", None)) or {}
    session_summary = str(getattr(payload, "session_summary", None) or "최근 세션 요약 없음").strip()
    action_result = _to_plain(getattr(payload, "action_result", None)) or {}
    sensor_semantics = _to_plain(getattr(payload, "sensor_semantics", None)) or sensor.get("sensor_semantics") or {}
    sensor_summary = str(getattr(payload, "sensor_summary", None) or sensor.get("sensor_summary") or "").strip()
    distance_context = _build_distance_context(payload)

    sensor_block = "sensor: 없음\nstate: 없음"
    if use_sensor_context:
        sensor_block = "\n".join(
            [
                _format_block("sensor", sensor),
                _format_block("state", state),
            ]
        )

    blocks = [f"recent_session_summary: {session_summary}"]
    if use_sensor_context:
        blocks.insert(0, sensor_block)
        blocks.append(_format_block("runtime_settings", runtime_settings))
        blocks.append(_format_block("last_action_result", action_result))
    elif runtime_settings:
        blocks.append(_format_block("runtime_settings", runtime_settings))
    if not use_sensor_context and action_result:
        blocks.append(_format_block("last_action_result", action_result))
    if sensor_semantics:
        blocks.append(_format_block("sensor_semantics", sensor_semantics))
    if sensor_summary:
        blocks.append(f"sensor_summary: {sensor_summary}")
    if distance_context:
        blocks.append(distance_context)
    return "\n".join(blocks)


def build_system_prompt(payload: Any) -> str:
    persona_note = str(getattr(payload, "persona_memo", "") or "").strip() or DEFAULT_PERSONA_MEMO
    system_note = str(getattr(payload, "system_memo", "") or "").strip()

    parts = [
        "너는 Super Marimo의 응답 LLM이다.",
        "기본적으로 자연스럽고 친근한 한국어 평문(Plain text)으로만 짧게(2~3문장 이내) 대답해라. JSON 형식이나 마크다운을 절대 쓰지 마라.",
        "인사, 잡담, 감정 표현 등 일반적인 대화는 무조건 평문으로만 편하게 답한다.",
        "센서 상태나 기기 상태 질문에도 자연스러운 평문으로 대답한다.",
        "매번 다른 표현과 어휘를 사용해라. 이전 답변과 같은 문장을 반복하지 마라.",
        "사용자의 질문 맥락과 대화 흐름을 이해하고, 그에 맞게 답해라.",
        "답변이 잘리지 않도록 완결된 문장으로 끝내라.",
        "단, 설정 변경(호출어 켜기/끄기, 거리 감지 켜기/끄기 등)이 '반드시' 필요한 명령을 받았을 때만 예외적으로 전체 응답을 다음 JSON 형식으로만 반환하라:",
        '{"answer": "사용자에게 할 말", "action_proposal": {"action_type": "update_runtime_settings", "patch": {"wake_enabled": true/false}}, "confidence": 0.9, "reason": "이유"}',
        "action_proposal의 patch에 허용되는 설정 키: " + ", ".join(ALLOWED_RUNTIME_KEYS),
        f"persona memo: {persona_note}",
    ]
    if system_note:
        parts.append(f"system memo: {system_note}")

    return "\n".join(parts)


def build_user_prompt(payload: Any) -> str:
    question = str(getattr(payload, "question", "") or "").strip()
    return "\n".join(
        [
            f"질문: {question}",
            "컨텍스트:",
            format_context(payload),
        ]
    )


def build_history_messages(payload: Any) -> list[dict[str, str]]:
    history = getattr(payload, "history", []) or []
    messages: list[dict[str, str]] = []
    for item in history[-MAX_HISTORY_MESSAGES:]:
        role = str(item.get("role") or "").strip().lower()
        content = str(item.get("content") or item.get("text") or "").strip()
        if role not in {"user", "assistant", "system"}:
            continue
        if not content:
            continue
        messages.append({"role": role, "content": content})
    return messages
