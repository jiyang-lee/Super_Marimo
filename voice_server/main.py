import logging
import os
import tempfile
import wave
from typing import Any

import numpy as np
import soundfile as sf
from fastapi import BackgroundTasks, FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from config import (
    MOCK_MODE,
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
    allow_methods=["*"],
    allow_headers=["*"],
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
    stt_models_status: dict[str, Any] = {}
    for key in ("fast", "accurate"):
        try:
            get_stt_model(key)
            stt_models_status[key] = {
                "loaded": True,
                "device": _STT_RUNTIME_STATES.get(key, {}).get("device", STT_DEVICE),
                "compute_type": _STT_RUNTIME_STATES.get(key, {}).get("compute_type", STT_COMPUTE_TYPE),
                "size": _STT_CONFIG[key]["size"],
            }
        except Exception:
            stt_models_status[key] = {
                "loaded": False,
                "device": None,
                "compute_type": None,
                "size": _STT_CONFIG[key]["size"],
            }

    return {
        "ok": True,
        "server": "voice",
        "mock_mode": MOCK_MODE,
        "stt_models": stt_models_status,
        "stt_device": STT_DEVICE,
        "stt_compute_type": STT_COMPUTE_TYPE,
        "tts_backend": TTS_BACKEND,
        "tts_model": TTS_MODEL_ID,
        "tts_voice_name": TTS_VOICE_NAME,
        "tts_voice_names": _TTS_RUNTIME_STATE.get("available_voice_names", []),
        "tts_lang": TTS_LANG,
        "tts_ready": _TTS_RUNTIME_STATE["ready"],
        "tts_runtime_voice_name": _TTS_RUNTIME_STATE["voice_name"],
        "tts_error": _TTS_RUNTIME_STATE["error"],
        "tts_cache_dir": str(SUPERTONIC_CACHE_DIR),
        "tts_model_dir": str(SUPERTONIC_MODEL_DIR),
    }


@app.post("/stt")
async def stt(audio: UploadFile = File(...), model: str = "fast") -> dict[str, Any]:
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
        }
    finally:
        os.remove(audio_path)


@app.post("/tts")
def tts(payload: TtsPayload, background_tasks: BackgroundTasks) -> FileResponse:
    if not payload.text.strip():
        raise HTTPException(status_code=400, detail="text is required")

    output_path = tempfile.NamedTemporaryFile(delete=False, suffix=".wav").name

    if MOCK_MODE:
        sample_rate = 16_000
        tone = np.zeros(sample_rate, dtype=np.float32)
        sf.write(output_path, tone, sample_rate)
        background_tasks.add_task(os.remove, output_path)
        return FileResponse(output_path, media_type="audio/wav", filename="mock_tts.wav")

    wav_bytes, _resolved_voice = synthesize(payload.text, voice_name=payload.voice_name)
    from supertonic import TTS
    tts_instance = get_tts_runtime()["tts"]
    TTS.save_audio(wav_bytes, output_path)
    background_tasks.add_task(os.remove, output_path)
    return FileResponse(output_path, media_type="audio/wav", filename="tts.wav")


@app.on_event("startup")
def startup_load_stt_models():
    if not MOCK_MODE:
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
            logger.info("Eager-loading TTS model and voice style...")
            runtime = get_tts_runtime()
            logger.info("TTS voice style ready: %s", runtime["voice_name"])
        except Exception as exc:
            _TTS_RUNTIME_STATE.update({"loaded": False, "ready": False, "error": str(exc)})
            logger.error("Failed to load TTS model: %s", exc)
            raise
