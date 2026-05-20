from __future__ import annotations

import re
from typing import Any

from config import MOCK_MODE


def _normalize(text: str) -> str:
    value = (text or "").lower()
    value = re.sub(r"\s+", " ", value)
    return value.strip()


def _summarize_sensor(payload: Any) -> str:
    sensor = getattr(payload, "sensor", None) or {}
    state = getattr(payload, "state", None) or {}
    values: list[str] = []
    for key, label in (
        ("temperature", "온도"),
        ("humidity", "습도"),
        ("light", "조도"),
        ("water_level", "수위"),
        ("distance", "거리"),
    ):
        if sensor.get(key) is not None:
            values.append(f"{label} {sensor[key]}")
    sensor_text = ", ".join(values) if values else "센서 값이 아직 없어요"
    level = state.get("level", "normal")
    return f"지금 상태는 {level}이에요. {sensor_text}."


def _infer_action_proposal(question: str) -> dict[str, Any] | None:
    normalized = _normalize(question)
    if not normalized:
        return None

    wake_off_cues = ("wake off", "wake 끄", "wake 꺼", "깨우기 꺼", "깨우기 끄")
    wake_on_cues = ("wake on", "wake 켜", "깨우기 켜", "깨우기 시작")
    distance_off_cues = ("distance detection off", "거리 감지 꺼", "거리감지 꺼", "거리 감지 끄")
    distance_on_cues = ("distance detection on", "거리 감지 켜", "거리감지 켜", "거리 감지 시작")
    voice_off_cues = ("web voice off", "web 음성 끄", "웹 음성 끄", "웹 보이스 끄", "음성 꺼")
    voice_on_cues = ("web voice on", "web 음성 켜", "웹 음성 켜", "웹 보이스 켜", "음성 켜")

    if any(cue in normalized for cue in wake_off_cues):
        return {
            "action_type": "update_runtime_settings",
            "patch": {"wake_enabled": False},
            "summary": "깨우기 기능을 껐어요.",
        }
    if any(cue in normalized for cue in wake_on_cues):
        return {
            "action_type": "update_runtime_settings",
            "patch": {"wake_enabled": True},
            "summary": "깨우기 기능을 켰어요.",
        }
    if any(cue in normalized for cue in distance_off_cues):
        return {
            "action_type": "update_runtime_settings",
            "patch": {"distance_detection_enabled": False},
            "summary": "거리 감지를 껐어요.",
        }
    if any(cue in normalized for cue in distance_on_cues):
        return {
            "action_type": "update_runtime_settings",
            "patch": {"distance_detection_enabled": True},
            "summary": "거리 감지를 켰어요.",
        }
    if any(cue in normalized for cue in voice_off_cues):
        return {
            "action_type": "update_runtime_settings",
            "patch": {"web_voice_enabled": False},
            "summary": "웹 음성을 껐어요.",
        }
    if any(cue in normalized for cue in voice_on_cues):
        return {
            "action_type": "update_runtime_settings",
            "patch": {"web_voice_enabled": True},
            "summary": "웹 음성을 켰어요.",
        }

    threshold_match = re.search(
        r"(?:threshold|기준|거리 기준|distance threshold)[^\d]{0,12}(\d+(?:\.\d+)?)\s*(?:cm|센치|센티|센티미터)?",
        normalized,
    )
    if threshold_match:
        value = float(threshold_match.group(1))
        if value > 0:
            return {
                "action_type": "update_runtime_settings",
                "patch": {"distance_threshold_cm": value},
                "summary": f"거리 기준을 {value:g}cm로 바꿨어요.",
            }

    return None


def build_mock_contract(payload: Any) -> dict[str, Any]:
    question = str(getattr(payload, "question", "") or "").strip()
    use_sensor_context = bool(getattr(payload, "use_sensor_context", False))
    action_proposal = _infer_action_proposal(question)

    if not use_sensor_context:
        answer = "센서 정보가 없어서 지금 상태를 바로 보기는 어려워요."
        if action_proposal is not None:
            answer = f"{answer} 요청하신 설정은 바꿔볼 수 있어요."
        return {
            "answer": answer,
            "action_proposal": action_proposal,
            "confidence": 0.45 if action_proposal is not None else 0.3,
            "reason": "센서 컨텍스트가 꺼져 있어도 질문 의도만으로 기본 판단을 만들었어요.",
        }

    answer = _summarize_sensor(payload)
    if action_proposal is not None:
        answer = f"{answer} 요청하신 설정을 바꿀게요."

    return {
        "answer": answer,
        "action_proposal": action_proposal,
        "confidence": 0.88 if action_proposal is not None else 0.66,
        "reason": "질문과 센서 상태를 함께 보고 답을 만들었어요.",
    }


def get_chain():
    from langchain_core.runnables import RunnableLambda

    if MOCK_MODE:
        return RunnableLambda(build_mock_contract)

    from model_engine import generate_contract

    return RunnableLambda(generate_contract)
