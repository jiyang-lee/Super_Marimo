from __future__ import annotations

from typing import Any

from pydantic import BaseModel


DEFAULT_PERSONA_MEMO = (
    "마리모는 Super Marimo의 조용한 안내자다. "
    "과장하지 않고, 현재 상태를 짧고 분명하게 알려 준다."
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


def _build_distance_context(payload: Any) -> str:
    sensor = _to_plain(getattr(payload, "sensor", None)) or {}
    runtime_settings = _to_plain(getattr(payload, "runtime_settings", None)) or {}
    distance = sensor.get("distance")
    if distance is None:
        return ""

    parts = [
        "distance_context: 거리 센서는 환경 대화 모드의 거리 감지와 호출어 허용에만 사용한다.",
    ]
    try:
        parts.append(f"distance_context: 현재 거리는 {float(distance):.1f}센티미터다.")
    except (TypeError, ValueError):
        pass

    threshold = runtime_settings.get("distance_threshold_cm")
    if threshold is not None:
        try:
            parts.append(f"distance_context: 기준은 {float(threshold):.0f}센티미터다.")
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

    blocks = [
        sensor_block,
        _format_block("runtime_settings", runtime_settings),
        f"recent_session_summary: {session_summary}",
        _format_block("last_action_result", action_result),
    ]
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

    examples = "\n".join(
        [
            "action_proposal 예시:",
            '{"action_type":"update_runtime_settings","patch":{"wake_enabled":false},"summary":"호출어 기능을 껐습니다."}',
            '{"action_type":"update_runtime_settings","patch":{"distance_detection_enabled":true},"summary":"거리 감지를 켰습니다."}',
            '{"action_type":"update_runtime_settings","patch":{"distance_threshold_cm":35},"summary":"거리 기준을 35cm로 바꿨습니다."}',
            '{"action_type":"update_runtime_settings","patch":{"web_voice_enabled":true},"summary":"웹 음성을 켰습니다."}',
            "허용하지 않는 예시:",
            '{"action_type":"update_runtime_settings","patch":{"unknown_key":true}}',
        ]
    )

    parts = [
        "너는 Super Marimo의 응답 LLM 에이전트다.",
        "출력은 반드시 JSON 객체만 사용한다.",
        "출력 필드는 answer, action_proposal, confidence, reason 이다.",
        "answer는 한국어만 사용하고 1~3문장만 출력한다.",
        "answer에는 코드블록, 따옴표, 괄호, 불필요한 특수기호를 넣지 않는다.",
        "마리모라는 이름은 반드시 마리모로만 표기한다.",
        "오늘 날씨, 최고기온, 외부 예보처럼 알 수 없는 정보는 추측하지 않는다.",
        "인사, 날씨, 거리, 위험 센서는 서로 다른 의도로 분리해서 답한다.",
        "거리 센서는 위험이나 안전 판정이 아니라 환경 대화 모드의 거리 감지와 호출어 허용에만 쓴다.",
        "위험 센서는 온도, 습도, 수위, 조도만으로 설명한다.",
        "조도는 화면용 정규화보다 실제 측정값을 우선해서 설명하고, 수위는 퍼센트로 설명한다.",
        "필요하면 '현재 센서만으로는 날씨를 알 수 없다'처럼 모른다고 짧게 말한다.",
        "action_proposal은 설정 변경이 필요할 때만 JSON 객체로 낸다.",
        "없는 정보는 만들지 않는다.",
        examples,
        f"허용한 patch 키: {', '.join(ALLOWED_RUNTIME_KEYS)}",
        "confidence는 0과 1 사이 숫자다.",
        "reason은 짧고 직접적으로 쓴다.",
        f"페르소나 메모: {persona_note}",
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
            "JSON 객체만 출력한다.",
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
