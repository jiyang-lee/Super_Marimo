from functools import lru_cache
from typing import Any

from config import (
    HF_TIMEOUT_SEC,
    HF_TOKEN,
    HF_TTS_ENDPOINT_URL,
    _TTS_RUNTIME,
    _TTS_RUNTIME_LOCK,
    _TTS_RUNTIME_STATE,
    logger,
    SUPERTONIC_MODEL_DIR,
    TTS_BACKEND,
    TTS_LANG,
    TTS_VOICE_NAME,
)
from hf_endpoint_client import decode_audio_payload, post_json


@lru_cache(maxsize=1)
def get_tts_model():
    from supertonic import TTS

    return TTS(auto_download=True, model="supertonic-3", model_dir=SUPERTONIC_MODEL_DIR)


def select_tts_voice_name(available_voice_names: list[str], requested_voice_name: str | None = None) -> str:
    requested = (requested_voice_name or "").strip()
    if requested and requested in available_voice_names:
        return requested
    if requested and requested not in available_voice_names:
        logger.warning("Requested TTS voice '%s' not available; falling back", requested)

    if TTS_VOICE_NAME in available_voice_names:
        return TTS_VOICE_NAME
    if available_voice_names:
        return available_voice_names[0]
    return requested or TTS_VOICE_NAME


def get_tts_runtime() -> dict[str, Any]:
    global _TTS_RUNTIME

    if _TTS_RUNTIME_STATE["ready"] and _TTS_RUNTIME is not None:
        return _TTS_RUNTIME

    with _TTS_RUNTIME_LOCK:
        if _TTS_RUNTIME_STATE["ready"] and _TTS_RUNTIME is not None:
            return _TTS_RUNTIME

        tts = get_tts_model()
        available_voice_names = list(getattr(tts, "voice_style_names", []) or [])
        voice_name = select_tts_voice_name(available_voice_names, TTS_VOICE_NAME)
        style = tts.get_voice_style(voice_name=voice_name)
        _TTS_RUNTIME = {
            "tts": tts,
            "style": style,
            "voice_name": voice_name,
            "available_voice_names": available_voice_names,
        }
        _TTS_RUNTIME_STATE.update(
            {
                "loaded": True,
                "ready": True,
                "voice_name": voice_name,
                "available_voice_names": available_voice_names,
                "error": None,
            }
        )
        return _TTS_RUNTIME


def synthesize(text: str, voice_name: str | None = None) -> tuple[bytes, str]:
    if HF_TTS_ENDPOINT_URL:
        try:
            resolved_voice_name = voice_name or TTS_VOICE_NAME
            payload, latency_ms = post_json(
                HF_TTS_ENDPOINT_URL,
                {"inputs": text, "text": text, "voice_name": resolved_voice_name, "lang": TTS_LANG},
                token=HF_TOKEN,
                timeout=HF_TIMEOUT_SEC,
            )
            wav_bytes = decode_audio_payload(payload)
            _TTS_RUNTIME_STATE.update(
                {
                    "loaded": True,
                    "ready": True,
                    "voice_name": resolved_voice_name,
                    "last_latency_ms": latency_ms,
                    "last_error": None,
                }
            )
            return wav_bytes, resolved_voice_name
        except Exception as exc:
            _TTS_RUNTIME_STATE.update({"ready": False, "last_error": str(exc)})
            logger.warning("HF TTS endpoint failed, falling back to local TTS: %s", exc)

    runtime = get_tts_runtime()
    tts = runtime["tts"]
    available_voice_names = runtime.get("available_voice_names", [])
    resolved_voice_name = select_tts_voice_name(available_voice_names, voice_name)
    style = tts.get_voice_style(voice_name=resolved_voice_name)
    wav, _duration = tts.synthesize(text, voice_style=style, lang=TTS_LANG)
    return wav, resolved_voice_name
