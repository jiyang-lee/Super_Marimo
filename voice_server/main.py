import logging
import os
import re
import tempfile
import wave
import sys
from pathlib import Path
from typing import Any

import numpy as np
import soundfile as sf
from fastapi import BackgroundTasks, FastAPI, File, HTTPException, UploadFile, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

CURRENT_DIR = Path(__file__).resolve().parent
if str(CURRENT_DIR) not in sys.path:
    sys.path.insert(0, str(CURRENT_DIR))
if "config" in sys.modules:
    del sys.modules["config"]

from config import (
    MOCK_MODE,
    RUN_MODE,
    HF_STT_BACKEND,
    HF_STT_ENDPOINT_URL,
    HF_STT_MODEL_ID,
    HF_TOKEN,
    HF_TTS_ENDPOINT_URL,
    STT_COMPUTE_TYPE,
    STT_DEVICE,
    STT_MODEL_SIZE,
    SUPERTONIC_CACHE_DIR,
    SUPERTONIC_MODEL_DIR,
    TTS_BACKEND,
    TTS_LANG,
    TTS_MODEL_ID,
    TTS_VOICE_NAME,
    _STT_CONFIG,
    _STT_HF_RUNTIME_STATE,
    _STT_RUNTIME_STATES,
    _TTS_RUNTIME_STATE,
    logger,
)
from stt_engine import get_stt_model, transcribe_audio
from tts_engine import get_tts_runtime, synthesize


app = FastAPI(title="Marimo Voice Server", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)


class PrivateNetworkCorsMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["Access-Control-Allow-Private-Network"] = "true"
        return response


app.add_middleware(PrivateNetworkCorsMiddleware)


class TtsPayload(BaseModel):
    text: str
    voice_name: str | None = None


def sanitize_tts_text(text: str) -> str:
    cleaned = text or ""
    cleaned = re.sub(r"[\u200b-\u200d\ufeff\ufe0e\ufe0f]", "", cleaned)
    cleaned = re.sub(r"[\x00-\x1f\x7f]", " ", cleaned)
    cleaned = re.sub(r"[^0-9가-힣\s]", " ", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned.strip()


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled voice-server error: %s", exc)
    return JSONResponse(
        status_code=500,
        content={"detail": str(exc), "type": exc.__class__.__name__},
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Private-Network": "true",
        },
    )


@app.get("/health")
def health() -> dict[str, Any]:
    return {"ok": True, "server": "voice"}


@app.get("/")
def root() -> JSONResponse:
    return JSONResponse(
        status_code=200,
        content={
            "ok": True,
            "server": "voice",
            "endpoints": ["/health", "/ready", "/stt", "/tts"],
        },
    )


@app.get("/favicon.ico")
def favicon() -> JSONResponse:
    return JSONResponse(status_code=204, content={})


@app.get("/ready")
def ready() -> JSONResponse:
    stt_models_status: dict[str, Any] = {}
    stt_external = HF_STT_BACKEND == "serverless" or bool(HF_STT_ENDPOINT_URL)
    backend = "mock" if MOCK_MODE else ("hf_endpoint" if (stt_external or HF_TTS_ENDPOINT_URL) else "local")
    if MOCK_MODE:
        for key in ("fast", "accurate"):
            stt_models_status[key] = {
                "loaded": True,
                "device": STT_DEVICE,
                "compute_type": STT_COMPUTE_TYPE,
                "size": _STT_CONFIG[key]["size"],
            }
        ready_state = True
        tts_ready = True
        tts_runtime_voice_name = TTS_VOICE_NAME
        tts_error = None
    else:
        for key in ("fast", "accurate"):
            stt_models_status[key] = {
                "loaded": stt_external or key in _STT_RUNTIME_STATES,
                "device": HF_STT_BACKEND if stt_external else _STT_RUNTIME_STATES.get(key, {}).get("device"),
                "compute_type": None if stt_external else _STT_RUNTIME_STATES.get(key, {}).get("compute_type"),
                "size": _STT_CONFIG[key]["size"],
            }
        tts_ready = bool(HF_TTS_ENDPOINT_URL) or _TTS_RUNTIME_STATE["ready"]
        ready_state = all(item["loaded"] for item in stt_models_status.values()) and tts_ready
        tts_runtime_voice_name = _TTS_RUNTIME_STATE["voice_name"]
        tts_error = _TTS_RUNTIME_STATE["error"]

    return JSONResponse(
        status_code=200 if ready_state else 503,
        content={
            "ok": ready_state,
            "ready": ready_state,
            "server": "voice",
            "run_mode": RUN_MODE,
            "mock_mode": MOCK_MODE,
            "backend": backend,
            "hf_stt_backend": HF_STT_BACKEND,
            "hf_stt_model_id": HF_STT_MODEL_ID,
            "hf_token_configured": bool(HF_TOKEN),
            "hf_stt_endpoint_configured": bool(HF_STT_ENDPOINT_URL),
            "hf_tts_endpoint_configured": bool(HF_TTS_ENDPOINT_URL),
            "hf_stt_last_latency_ms": _STT_HF_RUNTIME_STATE.get("last_latency_ms"),
            "hf_stt_last_error": _STT_HF_RUNTIME_STATE.get("last_error"),
            "stt_models": stt_models_status,
            "stt_device": STT_DEVICE,
            "stt_compute_type": STT_COMPUTE_TYPE,
            "tts_backend": TTS_BACKEND,
            "tts_model": TTS_MODEL_ID,
            "tts_voice_name": TTS_VOICE_NAME,
            "tts_voice_names": _TTS_RUNTIME_STATE.get("available_voice_names", []),
            "tts_lang": TTS_LANG,
            "tts_ready": tts_ready,
            "tts_runtime_voice_name": tts_runtime_voice_name,
            "tts_error": tts_error,
            "tts_last_latency_ms": _TTS_RUNTIME_STATE.get("last_latency_ms"),
            "tts_last_error": _TTS_RUNTIME_STATE.get("last_error"),
            "tts_cache_dir": str(SUPERTONIC_CACHE_DIR),
            "tts_model_dir": str(SUPERTONIC_MODEL_DIR),
        },
    )


@app.post("/stt")
async def stt(audio: UploadFile = File(...), model: str = "fast", session_id: str = Query(None)) -> dict[str, Any]:
    if model not in {"fast", "accurate"}:
        raise HTTPException(status_code=400, detail="model must be 'fast' or 'accurate'")

    if MOCK_MODE:
        return {"text": "모의 STT 결과입니다.", "segments": [], "mock": True, "model": model}

    suffix = os.path.splitext(audio.filename or "audio.wav")[1] or ".wav"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(await audio.read())
        audio_path = tmp.name

    try:
        try:
            with wave.open(audio_path, "rb") as wav_file:
                frame_rate = wav_file.getframerate() or 16000
                frame_count = wav_file.getnframes() or 0
                duration_sec = frame_count / float(frame_rate)
        except wave.Error:
            duration_sec = None

        if duration_sec is not None and duration_sec < 0.5:
            return {
                "text": "",
                "language": "ko",
                "segments": [],
                "mock": False,
                "model": model,
                "session_id": session_id,
                "warning": "audio_too_short",
            }

        segments, info = transcribe_audio(audio_path, model_key=model)
        segment_list = [
            {"start": segment.start, "end": segment.end, "text": segment.text}
            for segment in segments
        ]
        return {
            "text": " ".join(segment["text"].strip() for segment in segment_list).strip(),
            "language": info.language,
            "segments": segment_list,
            "mock": False,
            "model": model,
            "session_id": session_id,
        }
    finally:
        os.remove(audio_path)


@app.post("/tts")
def tts(payload: TtsPayload, background_tasks: BackgroundTasks) -> FileResponse:
    sanitized_text = sanitize_tts_text(payload.text)
    if not sanitized_text:
        raise HTTPException(status_code=400, detail="text is required")

    output_path = tempfile.NamedTemporaryFile(delete=False, suffix=".wav").name

    if MOCK_MODE:
        sample_rate = 16_000
        tone = np.zeros(sample_rate, dtype=np.float32)
        sf.write(output_path, tone, sample_rate)
        background_tasks.add_task(os.remove, output_path)
        return FileResponse(output_path, media_type="audio/wav", filename="mock_tts.wav")

    wav_bytes, _resolved_voice = synthesize(sanitized_text, voice_name=payload.voice_name)
    if isinstance(wav_bytes, (bytes, bytearray)) and bytes(wav_bytes[:4]) == b"RIFF":
        Path(output_path).write_bytes(bytes(wav_bytes))
    else:
        tts_instance = get_tts_runtime()["tts"]
        tts_instance.save_audio(wav_bytes, output_path)
    background_tasks.add_task(os.remove, output_path)
    return FileResponse(output_path, media_type="audio/wav", filename="tts.wav")


@app.on_event("startup")
def startup_load_stt_models():
    if MOCK_MODE:
        logger.info("Mock mode: skipping model eager-loading.")
        return
    if HF_STT_BACKEND == "serverless" and HF_TOKEN:
        _STT_HF_RUNTIME_STATE.update({"ready": True, "backend": "serverless", "model_id": HF_STT_MODEL_ID, "last_error": None})
        logger.info("HF serverless STT configured; skipping local STT eager-loading.")
    elif HF_STT_ENDPOINT_URL:
        _STT_HF_RUNTIME_STATE.update({"ready": True, "backend": "endpoint", "model_id": HF_STT_MODEL_ID, "last_error": None})
        logger.info("HF STT endpoint configured; skipping local STT eager-loading.")
    else:
        logger.info("Eager-loading STT models...")
        for key in ("fast", "accurate"):
            try:
                get_stt_model(key)
                state = _STT_RUNTIME_STATES.get(key, {})
                logger.info(
                    "STT model '%s' (%s) loaded on %s",
                    key,
                    _STT_CONFIG[key]["size"],
                    state.get("device", "unknown"),
                )
            except Exception as exc:
                logger.error("Failed to load STT model '%s': %s", key, exc)
    try:
        if HF_TTS_ENDPOINT_URL:
            _TTS_RUNTIME_STATE.update({"loaded": True, "ready": True, "error": None})
            logger.info("HF TTS endpoint configured; skipping local TTS eager-loading.")
        else:
            logger.info("Eager-loading TTS model and voice style...")
            runtime = get_tts_runtime()
            logger.info("TTS voice style ready: %s", runtime["voice_name"])
    except Exception as exc:
        _TTS_RUNTIME_STATE.update({"loaded": False, "ready": False, "error": str(exc)})
        logger.error("Failed to load TTS model: %s", exc)
        raise
