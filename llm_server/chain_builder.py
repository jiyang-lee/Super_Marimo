from __future__ import annotations

import re
from typing import Any

from config import MOCK_MODE
from contracts import build_contract


_GREETING_CUES = ("안녕", "안녕하세요", "반가워", "반갑", "hello", "hi")
_WEATHER_CUES = ("날씨", "weather", "오늘 날씨", "오늘 어때", "기온 어때")
_DISTANCE_CUES = ("거리", "가까이", "멀리", "위치", "호출어", "wake", "threshold", "follow-up", "follow up", "감지")
_RISK_CUES = ("상태", "기온", "온도", "습도", "수위", "조도", "빛", "물", "센서")

_GREETING_BANK = (
    "안녕하세요. 무엇을 도와드릴까요.",
    "반가워요. 지금 상태를 볼까요.",
    "안녕. 어떤 걸 확인해볼까요.",
    "반가워요. 바로 도와드릴게요.",
    "안녕하세요. 필요한 걸 말해 주세요.",
)


def _normalize(text: str) -> str:
    value = (text or "").lower()
    value = re.sub(r"\s+", " ", value)
    return value.strip()


def _coerce_float(value: Any) -> float | None:
    try:
        if value is None:
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _question_text(payload: Any) -> str:
    return str(getattr(payload, "question", "") or "").strip()


def _payload_dict(value: Any) -> dict[str, Any]:
    if value is None:
        return {}
    if hasattr(value, "model_dump"):
        return value.model_dump()
    if isinstance(value, dict):
        return value
    return {}


def _contains_any(text: str, cues: tuple[str, ...]) -> bool:
    return any(cue in text for cue in cues)


def _is_greeting_question(payload: Any) -> bool:
    question = _normalize(_question_text(payload))
    if not question:
        return False
    if _contains_any(question, _WEATHER_CUES) or _contains_any(question, _DISTANCE_CUES) or _contains_any(question, _RISK_CUES):
        return False
    if _contains_any(question, _GREETING_CUES):
        return True
    return len(question) <= 12 and any(cue in question for cue in ("안녕", "반가워"))


def _is_weather_question(payload: Any) -> bool:
    question = _normalize(_question_text(payload))
    if not question:
        return False
    return _contains_any(question, _WEATHER_CUES)


def _is_distance_question(payload: Any) -> bool:
    question = _normalize(_question_text(payload))
    if not question:
        return False
    return _contains_any(question, _DISTANCE_CUES)


def _is_sensor_risk_question(payload: Any) -> bool:
    question = _normalize(_question_text(payload))
    if not question:
        return False
    if _is_distance_question(payload) or _is_weather_question(payload):
        return False
    return _contains_any(question, _RISK_CUES) or "지금 상태" in question or "현재 상태" in question


def _greeting_contract(payload: Any) -> dict[str, Any]:
    question = _normalize(_question_text(payload))
    if "안녕하세요" in question:
        answer = "안녕하세요. 무엇을 도와드릴까요."
    elif "반가워" in question or "반갑" in question:
        answer = "반가워요. 지금 상태를 볼까요."
    elif "안녕" in question:
        answer = "안녕. 어떤 걸 확인해볼까요."
    else:
        index = sum(ord(ch) for ch in question) % len(_GREETING_BANK) if question else 0
        answer = _GREETING_BANK[index]
    return build_contract(
        answer=answer,
        action_proposal=None,
        confidence=0.99,
        reason="greeting",
    )


def _weather_contract(payload: Any) -> dict[str, Any]:
    sensor = _payload_dict(getattr(payload, "sensor", None))
    temperature = _coerce_float(sensor.get("temperature"))
    humidity = _coerce_float(sensor.get("humidity"))

    parts = ["현재 센서만으로는 오늘 날씨를 알 수 없습니다."]
    if temperature is not None:
        parts.append(f"지금 기온은 {temperature:.1f}도입니다.")
    if humidity is not None:
        parts.append(f"습도는 {humidity:.1f}퍼센트입니다.")

    return build_contract(
        answer=" ".join(parts),
        action_proposal=None,
        confidence=0.93,
        reason="weather_query_declined",
    )


def _risk_sensor_contract(payload: Any) -> dict[str, Any]:
    sensor = _payload_dict(getattr(payload, "sensor", None))
    state = _payload_dict(getattr(payload, "state", None))
    summary = str(getattr(payload, "sensor_summary", "") or sensor.get("sensor_summary") or "").strip()

    if summary:
        answer = summary
    else:
        temperature = _coerce_float(sensor.get("temperature"))
        humidity = _coerce_float(sensor.get("humidity"))
        water_level = _coerce_float(sensor.get("water_level_normalized_0_100"))
        if water_level is None:
            water_level = _coerce_float(sensor.get("water_level"))
        light = _coerce_float(sensor.get("light"))
        if light is None:
            light = _coerce_float(sensor.get("light_daytime_avg_13_18"))

        parts: list[str] = []
        level = str(state.get("level") or "normal").strip() or "normal"
        parts.append(f"현재 센서 상태는 {level}입니다.")
        if temperature is not None:
            parts.append(f"기온 {temperature:.1f}도")
        if humidity is not None:
            parts.append(f"습도 {humidity:.1f}퍼센트")
        if water_level is not None:
            parts.append(f"수위 {water_level:.1f}퍼센트")
        if light is not None:
            parts.append(f"조도 {light:.1f}럭스")
        answer = " / ".join(parts) if parts else "현재 센서 값을 아직 받지 못했습니다."

    return build_contract(
        answer=answer,
        action_proposal=None,
        confidence=0.9,
        reason="sensor_state_summary",
    )


def _distance_contract(payload: Any) -> dict[str, Any]:
    sensor = _payload_dict(getattr(payload, "sensor", None))
    runtime_settings = _payload_dict(getattr(payload, "runtime_settings", None))

    distance = _coerce_float(sensor.get("distance"))
    threshold = _coerce_float(runtime_settings.get("distance_threshold_cm"))
    inside = runtime_settings.get("distance_inside_threshold")
    distance_detection_enabled = bool(runtime_settings.get("distance_detection_enabled", True))
    wake_enabled = bool(runtime_settings.get("wake_enabled", True))

    parts = ["거리 센서는 환경 대화 모드의 거리 감지와 호출어 허용에만 사용됩니다."]
    if distance is not None:
        parts.append(f"현재 거리는 {distance:.1f}센티미터입니다.")
    if threshold is not None:
        try:
            parts.append(f"기준은 {float(threshold):.0f}센티미터입니다.")
        except (TypeError, ValueError):
            pass
    if inside is not None:
        parts.append("현재는 기준 안쪽입니다." if inside else "현재는 기준 바깥쪽입니다.")
    if not distance_detection_enabled:
        parts.append("거리 감지가 꺼져 있습니다.")
    elif not wake_enabled:
        parts.append("호출어가 꺼져 있습니다.")
    else:
        parts.append("호출어 허용 상태를 함께 보고 있습니다.")

    return build_contract(
        answer=" ".join(parts),
        action_proposal=None,
        confidence=0.9,
        reason="distance_context",
    )


def _infer_action_proposal(question: str) -> dict[str, Any] | None:
    normalized = _normalize(question)
    if not normalized:
        return None

    wake_off_cues = ("wake off", "wake disable", "호출어 끄", "호출어 비", "호출 끄")
    wake_on_cues = ("wake on", "wake enable", "호출어 켜", "호출어 시작")
    distance_off_cues = ("distance detection off", "거리 감지 끄", "거리감지 끄")
    distance_on_cues = ("distance detection on", "거리 감지 켜", "거리감지 켜")
    voice_off_cues = ("web voice off", "웹 음성 끄", "웹대화 끄")
    voice_on_cues = ("web voice on", "웹 음성 켜", "웹대화 켜")

    if any(cue in normalized for cue in wake_off_cues):
        return {
            "action_type": "update_runtime_settings",
            "patch": {"wake_enabled": False},
            "summary": "호출어 기능을 껐습니다.",
        }
    if any(cue in normalized for cue in wake_on_cues):
        return {
            "action_type": "update_runtime_settings",
            "patch": {"wake_enabled": True},
            "summary": "호출어 기능을 켰습니다.",
        }
    if any(cue in normalized for cue in distance_off_cues):
        return {
            "action_type": "update_runtime_settings",
            "patch": {"distance_detection_enabled": False},
            "summary": "거리 감지를 껐습니다.",
        }
    if any(cue in normalized for cue in distance_on_cues):
        return {
            "action_type": "update_runtime_settings",
            "patch": {"distance_detection_enabled": True},
            "summary": "거리 감지를 켰습니다.",
        }
    if any(cue in normalized for cue in voice_off_cues):
        return {
            "action_type": "update_runtime_settings",
            "patch": {"web_voice_enabled": False},
            "summary": "웹 음성을 껐습니다.",
        }
    if any(cue in normalized for cue in voice_on_cues):
        return {
            "action_type": "update_runtime_settings",
            "patch": {"web_voice_enabled": True},
            "summary": "웹 음성을 켰습니다.",
        }

    threshold_match = re.search(r"(?:threshold|거리|distance threshold)[^\d]{0,12}(\d+(?:\.\d+)?)\s*(?:cm|센티|센티미터)?", normalized)
    if threshold_match:
        value = float(threshold_match.group(1))
        if value > 0:
            return {
                "action_type": "update_runtime_settings",
                "patch": {"distance_threshold_cm": value},
                "summary": f"거리 기준을 {value:g}cm로 바꿨습니다.",
            }

    return None


def build_mock_contract(payload: Any) -> dict[str, Any]:
    question = _question_text(payload)
    use_sensor_context = bool(getattr(payload, "use_sensor_context", False))
    action_proposal = _infer_action_proposal(question)

    if _is_greeting_question(payload):
        return _greeting_contract(payload)

    if _is_weather_question(payload):
        return _weather_contract(payload)

    if _is_distance_question(payload):
        return _distance_contract(payload)

    if _is_sensor_risk_question(payload):
        if not use_sensor_context:
            answer = "현재 센서 정보를 바로 볼 수 없습니다."
            if action_proposal is not None:
                answer = f"{answer} 요청하신 설정은 바로 반영할 수 있습니다."
            return build_contract(
                answer=answer,
                action_proposal=action_proposal,
                confidence=0.45 if action_proposal is not None else 0.3,
                reason="sensor context is disabled",
            )
        return _risk_sensor_contract(payload)

    if not use_sensor_context:
        answer = "현재 센서 정보가 없어서 바로 답하기 어렵습니다."
        if action_proposal is not None:
            answer = f"{answer} 요청하신 설정은 바로 반영할 수 있습니다."
        return build_contract(
            answer=answer,
            action_proposal=action_proposal,
            confidence=0.45 if action_proposal is not None else 0.3,
            reason="sensor context is disabled",
        )

    sensor = _payload_dict(getattr(payload, "sensor", None))
    summary = str(getattr(payload, "sensor_summary", "") or sensor.get("sensor_summary") or "").strip()
    answer = summary or "현재 상태를 바로 읽을 수 있습니다."
    if action_proposal is not None:
        answer = f"{answer} 요청하신 설정은 바로 반영할 수 있습니다."

    return build_contract(
        answer=answer,
        action_proposal=action_proposal,
        confidence=0.88 if action_proposal is not None else 0.66,
        reason="sensor context summarized",
    )


def get_chain():
    from langchain_core.runnables import RunnableBranch, RunnableLambda

    default_chain = RunnableLambda(build_mock_contract if MOCK_MODE else generate_contract)
    return RunnableBranch(
        (lambda payload: _is_greeting_question(payload), RunnableLambda(_greeting_contract)),
        (lambda payload: _is_weather_question(payload), RunnableLambda(_weather_contract)),
        (lambda payload: _is_distance_question(payload), RunnableLambda(_distance_contract)),
        (lambda payload: _is_sensor_risk_question(payload), RunnableLambda(_risk_sensor_contract)),
        default_chain,
    )


def generate_contract(payload: Any) -> dict[str, Any]:
    from model_engine import generate_contract as _generate_contract

    return _generate_contract(payload)
