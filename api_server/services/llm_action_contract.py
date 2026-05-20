from __future__ import annotations

from typing import Any


_ALLOWED_PATCH_KEYS = {
    "wake_enabled",
    "distance_detection_enabled",
    "distance_threshold_cm",
    "web_voice_enabled",
}


def _coerce_bool(value: Any) -> bool | None:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"true", "1", "yes", "on", "켜", "켜기"}:
            return True
        if normalized in {"false", "0", "no", "off", "끄", "끄기"}:
            return False
    return None


def _coerce_float(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value.strip())
        except ValueError:
            return None
    return None


def describe_runtime_patch(patch: dict[str, Any]) -> str:
    parts: list[str] = []
    if "wake_enabled" in patch:
        parts.append("깨우기 기능을 켰어요." if patch["wake_enabled"] else "깨우기 기능을 껐어요.")
    if "distance_detection_enabled" in patch:
        parts.append("거리 감지를 켰어요." if patch["distance_detection_enabled"] else "거리 감지를 껐어요.")
    if "distance_threshold_cm" in patch:
        parts.append(f"거리 기준을 {float(patch['distance_threshold_cm']):g}cm로 바꿨어요.")
    if "web_voice_enabled" in patch:
        parts.append("웹 음성을 켰어요." if patch["web_voice_enabled"] else "웹 음성을 껐어요.")
    return " ".join(parts).strip()


def normalize_llm_action_proposal(action_proposal: Any) -> dict[str, Any] | None:
    if not isinstance(action_proposal, dict):
        return None

    action_type = str(action_proposal.get("action_type") or "").strip()
    if action_type != "update_runtime_settings":
        return None

    patch = action_proposal.get("patch")
    if not isinstance(patch, dict):
        return None

    normalized_patch: dict[str, Any] = {}
    for key, value in patch.items():
        if key not in _ALLOWED_PATCH_KEYS:
            continue
        if key == "distance_threshold_cm":
            numeric = _coerce_float(value)
            if numeric is None or numeric <= 0:
                continue
            normalized_patch[key] = numeric
            continue
        boolean = _coerce_bool(value)
        if boolean is not None:
            normalized_patch[key] = boolean

    if not normalized_patch:
        return None

    summary = str(action_proposal.get("summary") or "").strip()
    if not summary:
        summary = describe_runtime_patch(normalized_patch)
    return {
        "action_type": "update_runtime_settings",
        "patch": normalized_patch,
        "summary": summary,
    }


def compose_final_answer(answer: str, action_result: dict[str, Any] | None) -> str:
    if not action_result:
        return str(answer or "").strip()

    patch = action_result.get("patch") or {}
    if not isinstance(patch, dict):
        return str(answer or "").strip()

    # If no settings update action keys are present, return the original answer
    if not any(k in patch for k in _ALLOWED_PATCH_KEYS):
        return str(answer or "").strip()

    parts: list[str] = []

    # 1. Distance detection
    if "distance_detection_enabled" in patch:
        if patch["distance_detection_enabled"]:
            parts.append("거리 감지 모드를 켰어요. 필요하면 언제든 말씀해 주세요!")
        else:
            parts.append("거리 감지 모드를 껐어요. 필요하면 다시 켜주세요!")

    # 2. Wake-up word
    if "wake_enabled" in patch:
        if patch["wake_enabled"]:
            parts.append("깨우기 기능을 켰어요. 필요하면 언제든 말씀해 주세요!")
        else:
            parts.append("깨우기 기능을 껐어요. 필요하면 다시 켜주세요!")

    # 3. Web voice
    if "web_voice_enabled" in patch:
        if patch["web_voice_enabled"]:
            parts.append("웹 음성을 켰어요. 필요하면 언제든 말씀해 주세요!")
        else:
            parts.append("웹 음성을 껐어요. 필요하면 다시 켜주세요!")

    # 4. Distance threshold
    if "distance_threshold_cm" in patch:
        val = patch["distance_threshold_cm"]
        parts.append(f"거리 기준을 {float(val):g}cm로 바꿨어요. 필요하면 언제든 변경해 주세요!")

    if not parts:
        return str(answer or "").strip()

    return " ".join(parts)
