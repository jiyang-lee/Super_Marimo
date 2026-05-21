from functools import lru_cache

from config import (
    _STT_CONFIG,
    _STT_HF_RUNTIME_STATE,
    _STT_RUNTIME_STATES,
    HF_STT_BACKEND,
    HF_STT_ENDPOINT_URL,
    HF_STT_MODEL_ID,
    HF_TIMEOUT_SEC,
    HF_TOKEN,
    logger,
)
from hf_endpoint_client import HfEndpointError, post_bytes


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
        logger.warning("STT init failed for %s on %s, falling back to CPU: %s", model_key, device, message)
        _STT_RUNTIME_STATES[model_key] = {"device": "cpu", "compute_type": "int8"}
        return WhisperModel(size, device="cpu", compute_type="int8")


def get_stt_model(model_key: str = "fast"):
    return _load_stt_model(model_key)


def transcribe_audio(audio_path: str, model_key: str = "fast"):
    if HF_STT_BACKEND == "serverless" and HF_TOKEN:
        try:
            payload, latency_ms = transcribe_with_hf_serverless(audio_path)
            text, language, segments = normalize_hf_stt_response(payload)
            _STT_HF_RUNTIME_STATE.update(
                {
                    "ready": True,
                    "backend": "serverless",
                    "model_id": HF_STT_MODEL_ID,
                    "last_latency_ms": latency_ms,
                    "last_error": None,
                }
            )
            return segments, type("Info", (), {"language": language})()
        except Exception as exc:
            _STT_HF_RUNTIME_STATE.update({"ready": False, "last_error": str(exc)})
            logger.warning("HF serverless STT failed, trying next STT backend: %s", exc)

    if HF_STT_ENDPOINT_URL:
        try:
            with open(audio_path, "rb") as audio_file:
                payload, latency_ms = post_bytes(
                    HF_STT_ENDPOINT_URL,
                    audio_file.read(),
                    token=HF_TOKEN,
                    timeout=HF_TIMEOUT_SEC,
                    content_type="audio/wav",
                )
            text, language, segments = normalize_hf_stt_response(payload)
            _STT_HF_RUNTIME_STATE.update(
                {
                    "ready": True,
                    "backend": "endpoint",
                    "model_id": HF_STT_MODEL_ID,
                    "last_latency_ms": latency_ms,
                    "last_error": None,
                }
            )
            return segments, type("Info", (), {"language": language})()
        except Exception as exc:
            _STT_HF_RUNTIME_STATE.update({"ready": False, "last_error": str(exc)})
            logger.warning("HF STT endpoint failed, falling back to local STT: %s", exc)

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
        cfg = _STT_CONFIG[model_key]
        logger.warning("STT transcribe failed for %s, falling back to CPU: %s", model_key, message)
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


def transcribe_with_hf_serverless(audio_path: str):
    import time

    from huggingface_hub import InferenceClient

    client = InferenceClient(provider="hf-inference", api_key=HF_TOKEN)
    started = time.perf_counter()
    payload = client.automatic_speech_recognition(audio_path, model=HF_STT_MODEL_ID)
    latency_ms = (time.perf_counter() - started) * 1000
    return payload, latency_ms


class HfSttSegment:
    def __init__(self, start: float, end: float, text: str):
        self.start = start
        self.end = end
        self.text = text


def normalize_hf_stt_response(payload):
    if hasattr(payload, "model_dump"):
        payload = payload.model_dump()
    elif hasattr(payload, "dict"):
        payload = payload.dict()
    elif not isinstance(payload, (bytes, str, dict)) and hasattr(payload, "__dict__"):
        payload = vars(payload)

    if isinstance(payload, bytes):
        raise HfEndpointError("HF STT endpoint returned bytes, expected JSON")
    if isinstance(payload, str):
        return payload.strip(), "ko", [HfSttSegment(0.0, 0.0, payload.strip())] if payload.strip() else []
    if not isinstance(payload, dict):
        raise HfEndpointError(f"Unsupported HF STT response type: {type(payload).__name__}")

    text = str(payload.get("text") or payload.get("transcript") or "").strip()
    language = str(payload.get("language") or "ko")
    chunks = payload.get("chunks") or payload.get("segments") or []
    segments = []
    if isinstance(chunks, list):
        for chunk in chunks:
            if not isinstance(chunk, dict):
                continue
            chunk_text = str(chunk.get("text") or "").strip()
            timestamp = chunk.get("timestamp") or [chunk.get("start", 0.0), chunk.get("end", 0.0)]
            if isinstance(timestamp, (list, tuple)) and len(timestamp) >= 2:
                start, end = timestamp[0] or 0.0, timestamp[1] or 0.0
            else:
                start, end = 0.0, 0.0
            segments.append(HfSttSegment(float(start), float(end), chunk_text))
    if not segments and text:
        segments = [HfSttSegment(0.0, 0.0, text)]
    return text, language, segments
