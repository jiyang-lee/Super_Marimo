from __future__ import annotations

import re
from typing import Any, Optional

from services.runtime_settings import update_runtime_settings


_WAKE_OFF_PATTERNS = (
    r"wake\s*off",
    r"wake\s*끄",
    r"웨이크\s*끄",
    r"인사\s*끄",
    r"인사\s*하지\s*마",
    r"조용히\s*해",
)

_WAKE_ON_PATTERNS = (
    r"wake\s*on",
    r"wake\s*켜",
    r"웨이크\s*켜",
    r"인사\s*켜",
    r"인사\s*해",
)

_DISTANCE_OFF_PATTERNS = (
    r"distance\s*detection\s*off",
    r"거리\s*감지\s*끄",
    r"근접\s*감지\s*끄",
)

_DISTANCE_ON_PATTERNS = (
    r"distance\s*detection\s*on",
    r"거리\s*감지\s*켜",
    r"근접\s*감지\s*켜",
)

_VOICE_OFF_PATTERNS = (
    r"web\s*voice\s*off",
    r"web\s*음성\s*끄",
    r"웹\s*음성\s*끄",
    r"웹\s*보이스\s*끄",
    r"음성\s*꺼",
)

_VOICE_ON_PATTERNS = (
    r"web\s*voice\s*on",
    r"web\s*음성\s*켜",
    r"웹\s*음성\s*켜",
    r"웹\s*보이스\s*켜",
    r"음성\s*켜",
)


def _normalize(text: str) -> str:
    value = (text or "").lower()
    value = re.sub(r"\s+", " ", value)
    return value.strip()


def _match_any(text: str, patterns: tuple[str, ...]) -> bool:
    return any(re.search(pattern, text) for pattern in patterns)


def resolve_runtime_action(
    text: str,
    *,
    runtime_settings: dict[str, Any],
) -> Optional[dict[str, Any]]:
    normalized = _normalize(text)
    if not normalized:
        return None

    if _match_any(normalized, _WAKE_OFF_PATTERNS):
        return {
            "action_type": "update_runtime_settings",
            "patch": {"wake_enabled": False},
            "summary": "wake_enabled -> off",
            "source_text": text,
        }

    if _match_any(normalized, _WAKE_ON_PATTERNS):
        return {
            "action_type": "update_runtime_settings",
            "patch": {"wake_enabled": True},
            "summary": "wake_enabled -> on",
            "source_text": text,
        }

    if _match_any(normalized, _DISTANCE_OFF_PATTERNS):
        return {
            "action_type": "update_runtime_settings",
            "patch": {"distance_detection_enabled": False},
            "summary": "distance_detection_enabled -> off",
            "source_text": text,
        }

    if _match_any(normalized, _DISTANCE_ON_PATTERNS):
        return {
            "action_type": "update_runtime_settings",
            "patch": {"distance_detection_enabled": True},
            "summary": "distance_detection_enabled -> on",
            "source_text": text,
        }

    if _match_any(normalized, _VOICE_OFF_PATTERNS):
        return {
            "action_type": "update_runtime_settings",
            "patch": {"web_voice_enabled": False},
            "summary": "web_voice_enabled -> off",
            "source_text": text,
        }

    if _match_any(normalized, _VOICE_ON_PATTERNS):
        return {
            "action_type": "update_runtime_settings",
            "patch": {"web_voice_enabled": True},
            "summary": "web_voice_enabled -> on",
            "source_text": text,
        }

    threshold_match = re.search(
        r"(?:임계값|threshold|거리\s*기준|거리기준|distance\s*threshold)[^\d]{0,12}(\d+(?:\.\d+)?)\s*(?:cm|센티|센티미터)?",
        normalized,
    )
    if threshold_match:
        value = float(threshold_match.group(1))
        if value <= 0:
            return None
        return {
            "action_type": "update_runtime_settings",
            "patch": {"distance_threshold_cm": value},
            "summary": f"distance_threshold_cm -> {value:g}",
            "source_text": text,
        }

    explicit_cm_match = re.search(r"(\d+(?:\.\d+)?)\s*cm", normalized)
    if explicit_cm_match and any(
        cue in normalized for cue in ("설정", "조정", "바꿔", "변경", "맞춰", "threshold", "임계값")
    ):
        value = float(explicit_cm_match.group(1))
        if value > 0:
            return {
                "action_type": "update_runtime_settings",
                "patch": {"distance_threshold_cm": value},
                "summary": f"distance_threshold_cm -> {value:g}",
                "source_text": text,
            }

    return None


def apply_runtime_action(action: dict[str, Any], conn=None) -> dict[str, Any]:
    patch = dict(action.get("patch") or {})
    if not patch:
        raise ValueError("runtime action patch is empty")

    before = None
    try:
        before = action.get("before")
    except Exception:
        before = None

    after = update_runtime_settings(patch, conn=conn)
    return {
        "action_type": action.get("action_type") or "update_runtime_settings",
        "summary": action.get("summary") or "runtime settings updated",
        "patch": patch,
        "before": before,
        "after": after,
    }
