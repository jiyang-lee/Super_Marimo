import logging
import os
from pathlib import Path
from threading import Lock
from typing import Any

logger = logging.getLogger("voice_server")

RUN_MODE = os.getenv("RUN_MODE", os.getenv("MOCK_MODE", "false").lower() == "true" and "mock" or "gpu").lower()
MOCK_MODE = RUN_MODE == "mock"

STT_MODEL_SIZE = os.getenv("STT_MODEL_SIZE", "small")
STT_ACCURATE_MODEL_SIZE = os.getenv("STT_ACCURATE_MODEL_SIZE", "medium")
STT_DEVICE = os.getenv("WHISPER_DEVICE", "cpu" if RUN_MODE == "cpu" else "cuda")
STT_COMPUTE_TYPE = os.getenv("WHISPER_COMPUTE_TYPE", "int8" if RUN_MODE == "cpu" else "float16")
TTS_BACKEND = os.getenv("TTS_BACKEND", "mock" if RUN_MODE == "mock" else "supertonic-3")
TTS_MODEL_ID = os.getenv("TTS_MODEL_ID", "Supertone/supertonic-3")
TTS_VOICE_NAME = os.getenv("TTS_VOICE_NAME", "F1")
TTS_LANG = os.getenv("TTS_LANG", "ko")
HF_TOKEN = os.getenv("HF_TOKEN", "")
HF_STT_BACKEND = os.getenv("HF_STT_BACKEND", "serverless").lower()
HF_STT_MODEL_ID = os.getenv("HF_STT_MODEL_ID", "openai/whisper-large-v3")
HF_STT_ENDPOINT_URL = os.getenv("HF_STT_ENDPOINT_URL", "")
HF_TTS_ENDPOINT_URL = os.getenv("HF_TTS_ENDPOINT_URL", "")
HF_TIMEOUT_SEC = float(os.getenv("HF_TIMEOUT_SEC", "8"))
SUPERTONIC_CACHE_DIR = Path(os.getenv("SUPERTONIC_CACHE_DIR", "/root/.cache/supertonic3"))
SUPERTONIC_MODEL_DIR = SUPERTONIC_CACHE_DIR / TTS_BACKEND

_STT_CONFIG: dict[str, dict[str, str]] = {
    "fast": {"size": STT_MODEL_SIZE, "device": STT_DEVICE, "compute_type": STT_COMPUTE_TYPE},
    "accurate": {"size": STT_ACCURATE_MODEL_SIZE, "device": STT_DEVICE, "compute_type": STT_COMPUTE_TYPE},
}

_STT_RUNTIME_STATES: dict[str, dict[str, str]] = {}
_STT_HF_RUNTIME_STATE: dict[str, Any] = {
    "ready": bool(HF_STT_ENDPOINT_URL) or (HF_STT_BACKEND == "serverless" and bool(HF_TOKEN)),
    "backend": HF_STT_BACKEND,
    "model_id": HF_STT_MODEL_ID,
    "last_latency_ms": None,
    "last_error": None,
}
_TTS_RUNTIME_STATE: dict[str, Any] = {
    "loaded": False,
    "ready": False,
    "voice_name": TTS_VOICE_NAME,
    "available_voice_names": [],
    "error": None,
    "last_latency_ms": None,
    "last_error": None,
}
_TTS_RUNTIME_LOCK = Lock()
_TTS_RUNTIME: dict[str, Any] | None = None
