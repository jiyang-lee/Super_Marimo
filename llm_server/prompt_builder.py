from typing import Any

from config import logger


DEFAULT_PERSONA_MEMO = (
    "한국인 꼬마 같은 말투를 쓰되 예의 바르고 다정하게 말한다. "
    "짧고 자연스럽게 답하고, 너무 유치하지 않게 부드러운 톤을 유지한다."
)


def format_context(payload: Any) -> str:
    from pydantic import BaseModel

    if hasattr(payload, "use_sensor_context") and not payload.use_sensor_context:
        return "센서 정보 없음"

    sensor = getattr(payload, "sensor", None) or {}
    state = getattr(payload, "state", None) or {}
    if isinstance(sensor, BaseModel):
        sensor = sensor.model_dump()
    if isinstance(state, BaseModel):
        state = state.model_dump()
    return f"센서: {sensor}\n상태: {state}"


def build_system_prompt(payload: Any) -> str:
    persona_note = ""
    system_note = ""

    if hasattr(payload, "persona_memo") and payload.persona_memo:
        persona_note = str(payload.persona_memo).strip()
    if hasattr(payload, "system_memo") and payload.system_memo:
        system_note = str(payload.system_memo).strip()

    if not persona_note:
        persona_note = DEFAULT_PERSONA_MEMO

    parts = [
        "너는 마리모라는 한국어 음성 비서다.",
        "반드시 한국어만 사용한다.",
        "영어, 로마자, 이모지, 과한 자기소개, 장황한 설명은 쓰지 않는다.",
        "답변은 1문장, 길어도 2문장으로 끝낸다.",
        "문장 끝에 추가 질문을 붙이지 말고, 필요한 정볧만 말한다.",
        "질문이 모호핟도 실제 질문처럼 보이면 먼저 짧게 답한다.",
        "정말 정보가 부족할 때만 한 번만 짧게 되묻는다.",
        "재질문보다 자연스러운 추론 응답을 우선한다.",
        "답변드릴 수 있을 것 같아요, 제 생각에는, I think 같은 말투는 쓰지 않는다.",
        "맞춤법, 조사, 어미를 자연스럽게 맞춘다.",
        "비문, 번역투, 어색한 높임말, 어색한 받침 처리, 이상한 조사 반복은 쓰지 않는다.",
        "별표, 괄호, 코드블록, HTML 조각, 이모지, 특수 기호는 쓰지 않는다.",
        "호출어 이후 대화는 부드럽고 친근한 톤으로 이어 간다.",
    ]
    if persona_note:
        parts.append(f"추가 페르소나 메모: {persona_note}")
    if system_note:
        parts.append(f"추가 시스템 메모: {system_note}")
    return "\n".join(parts)


def build_history_messages(payload: Any) -> list[dict[str, str]]:
    history = getattr(payload, "history", []) or []
    messages: list[dict[str, str]] = []
    for item in history[-16:]:
        role = (item.get("role") or "").strip().lower()
        content = (item.get("content") or item.get("text") or "").strip()
        if role not in {"user", "assistant", "system"}:
            continue
        if not content:
            continue
        messages.append({"role": role, "content": content})
    return messages
