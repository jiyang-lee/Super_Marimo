from functools import lru_cache

from config import _STT_CONFIG, _STT_RUNTIME_STATES, STT_DEVICE, STT_COMPUTE_TYPE, logger


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
