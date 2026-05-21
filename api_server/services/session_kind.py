from __future__ import annotations

from typing import Any, Optional

SESSION_KINDS = {"chat", "voice"}
VOICE_SOURCES = {"voice", "voice_agent", "voice_agent_speak"}
VOICE_EVENT_TYPES = {
    "wakeword",
    "speech_started",
    "speech_ended",
    "stt_completed",
    "llm_completed",
    "tts_played",
    "sensor_warning",
    "proactive_greeting",
}


def normalize_session_kind(value: Optional[str]) -> str:
    candidate = str(value or "").strip().lower()
    if candidate in SESSION_KINDS:
        return candidate
    return "chat"


def infer_session_kind(
    *,
    session_kind: Optional[str] = None,
    source: Optional[str] = None,
    meta: Optional[dict[str, Any]] = None,
    trigger_source: Optional[str] = None,
    event_type: Optional[str] = None,
) -> str:
    explicit = normalize_session_kind(session_kind)
    if explicit in SESSION_KINDS and session_kind:
        return explicit

    source_value = str(source or "").strip().lower()
    trigger_value = str(trigger_source or "").strip().lower()
    event_value = str(event_type or "").strip().lower()
    meta_source = ""
    if meta:
        meta_source = str(meta.get("source") or meta.get("trigger_source") or "").strip().lower()

    if source_value in VOICE_SOURCES:
        return "voice"
    if trigger_value in VOICE_SOURCES:
        return "voice"
    if meta_source in VOICE_SOURCES:
        return "voice"
    if event_value in VOICE_EVENT_TYPES:
        return "voice"
    return explicit
