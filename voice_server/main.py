import logging
import os
import tempfile
import wave
from functools import lru_cache
from typing import Any

import numpy as np
import soundfile as sf
from fastapi import BackgroundTasks, FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request


MOCK_MODE = os.getenv("MOCK_MODE", "true").lower() == "true"
STT_MODEL_SIZE = os.getenv("STT_MODEL_SIZE", "small")
STT_ACCURATE_MODEL_SIZE = os.getenv("STT_ACCURATE_MODEL_SIZE", "medium")
STT_DEVICE = os.getenv("WHISPER_DEVICE", "cuda")
STT_COMPUTE_TYPE = os.getenv("WHISPER_COMPUTE_TYPE", "float16")
TTS_BACKEND = os.getenv("TTS_BACKEND", "supertonic-3")
TTS_MODEL_ID = os.getenv("TTS_MODEL_ID", "Supertone/supertonic-3")
TTS_VOICE_NAME = os.getenv("TTS_VOICE_NAME", "F1")
TTS_LANG = os.getenv("TTS_LANG", "ko")

_STT_CONFIG: dict[str, dict[str, str]] = {
    "fast": {"size": STT_MODEL_SIZE, "device": STT_DEVICE, "compute_type": STT_COMPUTE_TYPE},
    "accurate": {"size": STT_ACCURATE_MODEL_SIZE, "device": STT_DEVICE, "compute_type": STT_COMPUTE_TYPE},
}

_STT_RUNTIME_STATES: dict[str, dict[str, str]] = {}

logger = logging.getLogger("voice_server")

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


@lru_cache(maxsize=2)
def _load_stt_model(model_key: str):
    from faster_whisper import WhisperModel

    cfg = _STT_CONFIG[model_key]
    size = cfg["size"]
    device = cfg["device"]
    compute_type = cfg["compute_type"]

    try:
        model = WhisperModel(size, device=device, compute_type=compute_type)
        _STT_RUNTIME_STATES[model_key] = {"device": device, "compute_type": compute_type}
        return model
    except RuntimeError as exc:
        message = str(exc)
        if "libcublas.so.12" not in message and "cannot be loaded" not in message:
            raise
        logger.warning("CUDA STT init failed for %s, falling back to CPU: %s", model_key, message)
        _STT_RUNTIME_STATES[model_key] = {"device": "cpu", "compute_type": "int8"}
        return WhisperModel(size, device="cpu", compute_type="int8")


def get_stt_model(model_key: str = "fast"):
    return _load_stt_model(model_key)


def transcribe_audio(audio_path: str, model_key: str = "fast"):
    from faster_whisper import WhisperModel

    model = get_stt_model(model_key)
    try:
        segments, info = model.transcribe(
            audio_path,
            language="ko",
            beam_size=1,
            best_of=1,
            condition_on_previous_text=False,
            vad_filter=True,
            temperature=0.0,
        )
        return list(segments), info
    except RuntimeError as exc:
        message = str(exc)
        if "libcublas.so.12" not in message and "cannot be loaded" not in message:
            raise

        cfg = _STT_CONFIG[model_key]
        logger.warning("CUDA STT transcribe failed for %s, falling back to CPU: %s", model_key, message)
        _STT_RUNTIME_STATES[model_key] = {"device": "cpu", "compute_type": "int8"}
        _load_stt_model.cache_clear()
        cpu_model = WhisperModel(cfg["size"], device="cpu", compute_type="int8")
        segments, info = cpu_model.transcribe(
            audio_path,
            language="ko",
            beam_size=1,
            best_of=1,
            condition_on_previous_text=False,
            vad_filter=True,
            temperature=0.0,
        )
        return list(segments), info


@lru_cache(maxsize=1)
def get_tts_model():
    from supertonic import TTS

    return TTS(auto_download=True, model="supertonic-3")


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
        "tts_lang": TTS_LANG,
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

    tts = get_tts_model()
    style = tts.get_voice_style(voice_name=TTS_VOICE_NAME)
    wav, _duration = tts.synthesize(payload.text, voice_style=style, lang=TTS_LANG)
    tts.save_audio(wav, output_path)
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
