from __future__ import annotations

from typing import Any

from pydantic import BaseModel


DEFAULT_PERSONA_MEMO = (
    "마리모는 Super Marimo의 센서-LLM 에이전트다. "
    "짧고 자연스러운 한국어로 답하고, 안전한 설정 변경만 제안한다."
)

ALLOWED_RUNTIME_KEYS = (
    "wake_enabled",
    "distance_detection_enabled",
    "distance_threshold_cm",
    "web_voice_enabled",
)


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


def format_context(payload: Any) -> str:
    use_sensor_context = bool(getattr(payload, "use_sensor_context", False))
    sensor = _to_plain(getattr(payload, "sensor", None)) or {}
    state = _to_plain(getattr(payload, "state", None)) or {}
    runtime_settings = _to_plain(getattr(payload, "runtime_settings", None)) or {}
    session_summary = str(getattr(payload, "session_summary", None) or "최근 세션 요약 없음").strip()
    action_result = _to_plain(getattr(payload, "action_result", None)) or {}

    sensor_block = "sensor: 없음\nstate: 없음"
    if use_sensor_context:
        sensor_block = "\n".join(
            [
                _format_block("sensor", sensor),
                _format_block("state", state),
            ]
        )

    return "\n".join(
        [
            sensor_block,
            _format_block("runtime_settings", runtime_settings),
            f"recent_session_summary: {session_summary}",
            _format_block("last_action_result", action_result),
        ]
    )


def build_system_prompt(payload: Any) -> str:
    persona_note = str(getattr(payload, "persona_memo", "") or "").strip() or DEFAULT_PERSONA_MEMO
    system_note = str(getattr(payload, "system_memo", "") or "").strip()

    examples = "\n".join(
        [
            "허용된 action_proposal 예시:",
            '{"action_type":"update_runtime_settings","patch":{"wake_enabled":false},"summary":"깨우기 기능을 껐어요."}',
            '{"action_type":"update_runtime_settings","patch":{"distance_detection_enabled":true},"summary":"거리 감지를 켰어요."}',
            '{"action_type":"update_runtime_settings","patch":{"distance_threshold_cm":35},"summary":"거리 기준을 35cm로 바꿨어요."}',
            '{"action_type":"update_runtime_settings","patch":{"web_voice_enabled":true},"summary":"웹 음성을 켰어요."}',
            "허용되지 않는 예시(절대 쓰지 마라):",
            '{"action_type":"update_runtime_settings","patch":{"unknown_key":true}}',
        ]
    )
    parts = [
        "너는 Super Marimo의 센서-LLM 에이전트다.",
        "반드시 JSON 객체 하나만 출력한다.",
        "설명 문장, 마크다운, 코드블록, 목록을 쓰지 않는다.",
        "출력 필드는 answer, action_proposal, confidence, reason 이다.",
        "answer 는 사람이 읽기 쉬운 짧은 한국어로 쓴다. (한국인 꼬마처럼 다정하고 자연스럽게 대화)",
        "사용자가 '안녕', '뭐해', '반가워' 같은 일상 인사나 친근한 말을 건넬 때는, 센서(수위, 조도 등) 상태를 구구절절 언급하지 말고 귀엽고 따뜻한 일상 대답만 건네라.",
        "센서 상태(수위, 온도 등)는 사용자가 센서 상태를 구체적으로 물어보거나, 현재 상태 레벨(state)이 'danger'나 'warning' 같은 긴급한 상황일 때에만 언급하라.",
        "말투가 어색하거나 '상태이므로'와 같이 미완성되고 기계적인 문장은 절대로 뱉지 말고 자연스러운 구어체 문장으로 마쳐라.",
        "action_proposal 은 필요할 때만 객체로 쓰고, 아니면 null 로 둔다.",
        examples,
        "허용된 patch 키는 wake_enabled, distance_detection_enabled, distance_threshold_cm, web_voice_enabled 뿐이다.",
        "허용되지 않은 키를 쓰면 서버가 action_proposal을 거부한다.",
        "질문이 정보 요청이면 action_proposal 은 null 로 둔다.",
        "confidence 는 0과 1 사이 숫자다.",
        "reason 은 왜 그렇게 판단했는지 한 줄로 쓴다.",
        f"역할 메모: {persona_note}",
    ]
    if system_note:
        parts.append(f"시스템 메모: {system_note}")
    return "\n".join(parts)


def build_user_prompt(payload: Any) -> str:
    question = str(getattr(payload, "question", "") or "").strip()
    return "\n".join(
        [
            f"질문: {question}",
            "컨텍스트:",
            format_context(payload),
            "허용된 patch 키만 사용하고, JSON 객체만 출력하라.",
        ]
    )


def build_history_messages(payload: Any) -> list[dict[str, str]]:
    history = getattr(payload, "history", []) or []
    messages: list[dict[str, str]] = []
    for item in history[-16:]:
        role = str(item.get("role") or "").strip().lower()
        content = str(item.get("content") or item.get("text") or "").strip()
        if role not in {"user", "assistant", "system"}:
            continue
        if not content:
            continue
        messages.append({"role": role, "content": content})
    return messages
