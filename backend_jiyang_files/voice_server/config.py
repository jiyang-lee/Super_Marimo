import logging
import os
from pathlib import Path
from threading import Lock
from typing import Any

logger = logging.getLogger("voice_server")

RUN_MODE = os.getenv("RUN_MODE", os.getenv("MOCK_MODE", "true").lower() == "true" and "mock" or "gpu").lower()
MOCK_MODE = RUN_MODE == "mock"

STT_MODEL_SIZE = os.getenv("STT_MODEL_SIZE", "small")
STT_ACCURATE_MODEL_SIZE = os.getenv("STT_ACCURATE_MODEL_SIZE", "medium")
STT_DEVICE = os.getenv("WHISPER_DEVICE", "cpu" if RUN_MODE == "cpu" else "cuda")
STT_COMPUTE_TYPE = os.getenv("WHISPER_COMPUTE_TYPE", "int8" if RUN_MODE == "cpu" else "float16")
TTS_BACKEND = os.getenv("TTS_BACKEND", "mock" if RUN_MODE == "mock" else "supertonic-3")
TTS_MODEL_ID = os.getenv("TTS_MODEL_ID", "Supertone/supertonic-3")
TTS_VOICE_NAME = os.getenv("TTS_VOICE_NAME", "F1")
TTS_LANG = os.getenv("TTS_LANG", "ko")
SUPERTONIC_CACHE_DIR = Path(os.getenv("SUPERTONIC_CACHE_DIR", "/root/.cache/supertonic3"))
SUPERTONIC_MODEL_DIR = SUPERTONIC_CACHE_DIR / TTS_BACKEND

_STT_CONFIG: dict[str, dict[str, str]] = {
    "fast": {"size": STT_MODEL_SIZE, "device": STT_DEVICE, "compute_type": STT_COMPUTE_TYPE},
    "accurate": {"size": STT_ACCURATE_MODEL_SIZE, "device": STT_DEVICE, "compute_type": STT_COMPUTE_TYPE},
}

_STT_RUNTIME_STATES: dict[str, dict[str, str]] = {}
_TTS_RUNTIME_STATE: dict[str, Any] = {
    "loaded": False,
    "ready": False,
    "voice_name": TTS_VOICE_NAME,
    "available_voice_names": [],
    "error": None,
}
_TTS_RUNTIME_LOCK = Lock()
_TTS_RUNTIME: dict[str, Any] | None = None
