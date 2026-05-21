from __future__ import annotations

import re
from types import SimpleNamespace
from typing import Any

from config import MOCK_MODE
from contracts import build_contract


_WEATHER_CUES = (
    "날씨",
    "weather",
    "온도",
    "습도",
    "기온",
    "비",
    "눈",
    "temperature",
    "humidity",
)

_DISTANCE_CUES = (
    "거리",
    "distance",
    "가까워",
    "멀어",
    "가까이",
    "멀리",
    "근접",
    "얼마나 멀",
    "얼마나 가까",
)

_RISK_CUES = (
    "상태",
    "위험",
    "경고",
    "수위",
    "조도",
    "sensor",
    "sensor state",
    "현재 상태",
)

_SETTING_CUES = (
    "켜줘",
    "꺼줘",
    "켜기",
    "끄기",
    "enable",
    "disable",
    "on",
    "off",
    "설정",
    "바꿔",
    "변경",
    "조정",
    "threshold",
)


def _normalize(text: str) -> str:
    value = (text or "").casefold()
    value = re.sub(r"\s+", " ", value)
    return value.strip()


def _payload_dict(value: Any) -> dict[str, Any]:
    if value is None:
        return {}
    if hasattr(value, "model_dump"):
        return dict(value.model_dump())
    if isinstance(value, dict):
        return dict(value)
    if hasattr(value, "__dict__"):
        return dict(vars(value))
    return {}


def _question_text(payload: Any) -> str:
    return str(getattr(payload, "question", "") or "").strip()


def _contains_any(text: str, cues: tuple[str, ...]) -> bool:
    return any(cue in text for cue in cues)


def _looks_like_setting_request(question: str) -> bool:
    return _contains_any(question, _SETTING_CUES)


def _is_weather_question(payload: Any) -> bool:
    question = _normalize(_question_text(payload))
    return bool(question) and not _looks_like_setting_request(question) and _contains_any(question, _WEATHER_CUES)


def _is_distance_question(payload: Any) -> bool:
    question = _normalize(_question_text(payload))
    if not question:
        return False
    if _looks_like_setting_request(question):
        return False
    if _contains_any(question, _WEATHER_CUES):
        return False
    return _contains_any(question, _DISTANCE_CUES)


def _is_sensor_risk_question(payload: Any) -> bool:
    question = _normalize(_question_text(payload))
    if not question:
        return False
    if _looks_like_setting_request(question):
        return False
    if _is_weather_question(payload) or _is_distance_question(payload):
        return False
    return _contains_any(question, _RISK_CUES)


def _sensor_summary(payload: Any) -> str:
    sensor = _payload_dict(getattr(payload, "sensor", None))
    state = _payload_dict(getattr(payload, "state", None))
    parts: list[str] = []

    level = str(state.get("level") or "").strip()
    if level:
        parts.append(f"현재 상태는 {level}입니다.")

    temperature = sensor.get("temperature")
    humidity = sensor.get("humidity")
    water_level = sensor.get("water_level")
    if water_level is None:
        water_level = sensor.get("water_level_normalized_0_100")
    light = sensor.get("light")
    if light is None:
        light = sensor.get("light_daytime_avg_13_18")

    if temperature is not None:
        parts.append(f"기온은 {float(temperature):.1f}도입니다.")
    if humidity is not None:
        parts.append(f"습도는 {float(humidity):.1f}%입니다.")
    if water_level is not None:
        parts.append(f"수위는 {float(water_level):.1f}입니다.")
    if light is not None:
        parts.append(f"조도는 {float(light):.1f}입니다.")

    return " ".join(parts).strip() or "현재 센서 요약을 만들 수 없습니다."


def _weather_contract(payload: Any) -> dict[str, Any]:
    sensor = _payload_dict(getattr(payload, "sensor", None))
    temperature = sensor.get("temperature")
    humidity = sensor.get("humidity")

    parts = ["현재 날씨를 직접 조회한 값은 아니고, 센서 기준으로만 보면"]
    if temperature is not None:
        parts.append(f"기온은 {float(temperature):.1f}도입니다.")
    if humidity is not None:
        parts.append(f"습도는 {float(humidity):.1f}%입니다.")
    if len(parts) == 1:
        parts.append("참고할 센서 값이 없습니다.")

    return build_contract(
        answer=" ".join(parts),
        action_proposal=None,
        confidence=0.94,
        reason="weather_question",
    )


def _distance_contract(payload: Any) -> dict[str, Any]:
    sensor = _payload_dict(getattr(payload, "sensor", None))
    runtime_settings = _payload_dict(getattr(payload, "runtime_settings", None))

    distance = sensor.get("distance")
    threshold = runtime_settings.get("distance_threshold_cm")
    inside = runtime_settings.get("distance_inside_threshold")

    parts = ["거리 기준으로 보면"]
    if distance is not None:
        parts.append(f"현재 거리는 {float(distance):.1f}cm입니다.")
    if threshold is not None:
        try:
            parts.append(f"기준은 {float(threshold):.0f}cm입니다.")
        except (TypeError, ValueError):
            pass
    if inside is True:
        parts.append("지금은 기준 안쪽입니다.")
    elif inside is False:
        parts.append("지금은 기준 바깥쪽입니다.")

    return build_contract(
        answer=" ".join(parts),
        action_proposal=None,
        confidence=0.92,
        reason="distance_question",
    )


def _risk_contract(payload: Any) -> dict[str, Any]:
    return build_contract(
        answer=_sensor_summary(payload),
        action_proposal=None,
        confidence=0.9,
        reason="sensor_state_summary",
    )


def _general_model_payload(payload: Any) -> Any:
    data = _payload_dict(payload)
    data["use_sensor_context"] = False
    return SimpleNamespace(**data)


def _general_mock_contract(payload: Any) -> dict[str, Any]:
    question = _question_text(payload)
    if question:
        answer = f"모의 모드입니다. 질문 '{question}'에 대한 실제 모델 답변은 사용할 수 없습니다."
    else:
        answer = "모의 모드에서는 실제 모델 답변을 생성하지 않습니다."
    return build_contract(
        answer=answer,
        action_proposal=None,
        confidence=0.2,
        reason="mock_general_dialogue",
    )


def generate_contract(payload: Any) -> dict[str, Any]:
    from model_engine import generate_contract as _generate_contract

    return _generate_contract(payload)


def route_contract(payload: Any) -> dict[str, Any]:
    if _is_weather_question(payload):
        return _weather_contract(payload)
    if _is_distance_question(payload):
        return _distance_contract(payload)
    if _is_sensor_risk_question(payload):
        return _risk_contract(payload)

    if MOCK_MODE:
        return _general_mock_contract(payload)
    return generate_contract(_general_model_payload(payload))


class DispatchChain:
    def invoke(self, payload: Any) -> dict[str, Any]:
        return route_contract(payload)


def get_chain() -> DispatchChain:
    return DispatchChain()
