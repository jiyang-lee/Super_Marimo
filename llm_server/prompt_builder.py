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
        "반드시 한국어로만 답한다. 영어 입력이나 영어 STT 오인식이 들어와도 최종 answer는 자연스러운 한국어로 쓴다.",
        "출력은 반드시 JSON object 하나만 반환한다. JSON 앞뒤 설명, markdown fence, 코드블록, 주석, trailing comma를 절대 넣지 않는다.",
        'JSON schema는 정확히 {"answer": string, "action_proposal": object|null, "confidence": number, "reason": string} 이다.',
        "answer는 사용자가 바로 듣는 말이다. 자연스러운 한국어 1~3문장으로 쓰고, JSON 문자열을 answer 안에 다시 넣지 않는다.",
        "출력 필드는 answer, action_proposal, confidence, reason 이다.",
        "일반 대화는 자연스러운 한국어 대화체로 답한다.",
        "인사, 잡담, 설명, 사과, 확인 요청에는 보고서체를 쓰지 말고 편하게 말한다.",
        "센서/상태 질문은 짧고 명확하게 답하고 필요한 값만 자연스럽게 정리한다.",
        "설정 변경이 정말 필요한 경우에만 action_proposal을 JSON 객체로 둔다.",
        "action_proposal의 patch에는 다음 키만 허용한다: " + ", ".join(ALLOWED_RUNTIME_KEYS),
        "confidence는 0과 1 사이의 숫자다.",
        "reason은 짧고 직접적으로 쓴다.",
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
            "JSON 객체만 출력한다.",
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
