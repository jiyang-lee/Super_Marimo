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

_DEMO_MOOD_CUES = ("기분", "어때")
_DEMO_ROLE_CUES = ("뭘 할 수 있어", "뭐 할 수 있어", "무엇을 할 수 있어")
_DEMO_SING_CUES = ("노래", "랩", "장기자랑")
_CARE_GUIDE_CUES = ("팁", "가이드", "키우기", "관리", "어떻게 키워")
_PROACTIVE_GREETING_CUES = ("proactive_greeting_distance",)


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


def _is_demo_mood_question(question: str) -> bool:
    return all(cue in question for cue in _DEMO_MOOD_CUES)

def _is_demo_role_question(question: str) -> bool:
    return _contains_any(question, _DEMO_ROLE_CUES)

def _is_demo_sing_question(question: str) -> bool:
    return _contains_any(question, _DEMO_SING_CUES)

def _is_care_guide_question(question: str) -> bool:
    return _contains_any(question, _CARE_GUIDE_CUES)

def _is_proactive_greeting(question: str) -> bool:
    return _contains_any(question, _PROACTIVE_GREETING_CUES)


def _sensor_summary(payload: Any) -> str:
    sensor = _payload_dict(getattr(payload, "sensor", None))
    state = _payload_dict(getattr(payload, "state", None))
    parts: list[str] = []

    level = str(state.get("level") or "").strip()
    if level:
        parts.append(f"현재 상태는 {level}입니다.")

    temperature = sensor.get("temperature")
    humidity = sensor.get("humidity")
    water_level = sensor.get("water_level_normalized_0_100")
    if water_level is None:
        water_level = sensor.get("water_level_recent_avg_2h")
    if water_level is None:
        water_level = sensor.get("water_level")
    light = sensor.get("light_normalized_0_100")
    if light is None:
        light = sensor.get("light_daytime_avg_13_18")
    if light is None:
        light = sensor.get("light")

    if temperature is not None:
        parts.append(f"기온은 {float(temperature):.1f}도입니다.")
    if humidity is not None:
        parts.append(f"습도는 {float(humidity):.1f}%입니다.")
    if water_level is not None:
        parts.append(f"수위는 {float(water_level):.1f}%입니다.")
    if light is not None:
        parts.append(f"조도는 {float(light):.1f}%입니다.")

    return " ".join(parts).strip() or "현재 소스 세부 정보를 읽을 수 없습니다."


def _weather_contract(payload: Any) -> dict[str, Any]:
    sensor = _payload_dict(getattr(payload, "sensor", None))
    temperature = sensor.get("temperature")
    humidity = sensor.get("humidity")
    light = sensor.get("light") or sensor.get("light_normalized_0_100")
    question = _normalize(_question_text(payload))

    parts = []
    # 개별 센서 질문 매칭
    if "온도" in question or "기온" in question:
        if temperature is not None:
            parts.append(f"현재 온도는 {float(temperature):.1f}도입니다.")
    if "습도" in question:
        if humidity is not None:
            parts.append(f"현재 실내 습도는 {float(humidity):.1f}%입니다.")
    if "조도" in question or "밝기" in question:
        if light is not None:
            parts.append(f"현재 조도는 {float(light):.1f}%로 측정되네요.")

    # 특정 센서를 지칭하지 않고 날씨 전체를 물어본 경우
    if not parts:
        if temperature is not None:
            parts.append(f"기온은 {float(temperature):.1f}도,")
        if humidity is not None:
            parts.append(f"습도는 {float(humidity):.1f}%입니다.")
        if len(parts) == 0:
            parts.append("지금은 센서 정보를 읽을 수 없어요.")

    return build_contract(
        answer=" ".join(parts).strip(),
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


def _demo_mood_contract(payload: Any) -> dict[str, Any]:
    sensor = _payload_dict(getattr(payload, "sensor", None))
    temperature = sensor.get("temperature", 24.0)
    humidity = sensor.get("humidity", 50.0)
    # 온도, 습도 값 포맷팅 방어
    temp_str = f"{int(round(float(temperature)))}" if temperature is not None else "24"
    hum_str = f"{int(round(float(humidity)))}" if humidity is not None else "50"
    answer = f"오늘 온도는 {temp_str}도, 습도는 {hum_str}퍼센트로, 환경이 적절해서 기분이 좋아요!"
    return build_contract(answer=answer, action_proposal=None, confidence=1.0, reason="demo_mood")


def _demo_role_contract(payload: Any) -> dict[str, Any]:
    answer = "저는 사용자님의 마리모 키우기 가이드가 될 수 있답니다! 저와 함께 초보 식집사를 탈출해요!"
    return build_contract(answer=answer, action_proposal=None, confidence=1.0, reason="demo_role")


def _demo_sing_contract(payload: Any) -> dict[str, Any]:
    answer = "동글동글 마리모~ 예압~ 물 속에서 춤을 춰~ 햇빛 한 줌, 시원한 물이면 충분해~ 요! 피스!"
    return build_contract(answer=answer, action_proposal=None, confidence=1.0, reason="demo_sing")


def _care_guide_contract(payload: Any) -> dict[str, Any]:
    answer = "마리모는 일주일에 한 번씩 시원한 물로 갈아주시고, 직사광선을 피해 밝은 그늘에 두시는 게 좋아요."
    return build_contract(answer=answer, action_proposal=None, confidence=1.0, reason="care_guide")


def _proactive_greeting_contract(payload: Any) -> dict[str, Any]:
    state = _payload_dict(getattr(payload, "state", None))
    level = str(state.get("level") or "normal").strip().lower()
    sensor = _payload_dict(getattr(payload, "sensor", None))
    temp = sensor.get("temperature", 24.0)
    hum = sensor.get("humidity", 50.0)
    
    if level == "normal":
        answer = f"오늘도 마리모를 잘 돌봐주고 계시네요! 온도 {int(round(float(temp)))}도, 습도 {int(round(float(hum)))}퍼센트로 아주 쾌적해요!"
    else:
        alerts = state.get("alerts", [])
        if alerts:
            issue = str(alerts[0]).replace("_", " ")
            answer = f"저에게 관심을 가져주셔서 고마워요. 지금 {issue} 상태이니 물을 갈아주시거나 위치를 옮겨주시면 좋겠어요!"
        else:
            answer = "저에게 관심을 가져주셔서 고마워요. 환경이 조금 불편한 것 같으니 한번 확인해 주시겠어요?"

    return build_contract(answer=answer, action_proposal=None, confidence=1.0, reason="proactive_greeting")


def _general_model_payload(payload: Any) -> Any:
    data = _payload_dict(payload)
    data["use_sensor_context"] = False
    data["sensor"] = None
    data["state"] = None
    data["runtime_settings"] = None
    data["action_result"] = None
    return SimpleNamespace(**data)


def _setting_model_payload(payload: Any) -> Any:
    data = _payload_dict(payload)
    data["use_sensor_context"] = False
    data["sensor"] = None
    data["state"] = None
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
    q = _normalize(_question_text(payload))

    # Demo Script Interceptors
    if _is_demo_mood_question(q):
        return _demo_mood_contract(payload)
    if _is_demo_role_question(q):
        return _demo_role_contract(payload)
    if _is_demo_sing_question(q):
        return _demo_sing_contract(payload)
    if _is_care_guide_question(q):
        return _care_guide_contract(payload)
    if _is_proactive_greeting(q):
        return _proactive_greeting_contract(payload)

    if _is_weather_question(payload):
        return _weather_contract(payload)
    if _is_distance_question(payload):
        return _distance_contract(payload)
    if _is_sensor_risk_question(payload):
        return _risk_contract(payload)

    if _looks_like_setting_request(q):
        return generate_contract(_setting_model_payload(payload))

    if MOCK_MODE:
        return _general_mock_contract(payload)
    return generate_contract(_general_model_payload(payload))


class DispatchChain:
    def invoke(self, payload: Any) -> dict[str, Any]:
        return route_contract(payload)


def get_chain() -> DispatchChain:
    return DispatchChain()
