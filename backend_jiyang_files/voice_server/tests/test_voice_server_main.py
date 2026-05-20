import json
import sys
import types
from importlib import util
from pathlib import Path


_ORIGINAL_MODULES = {
    name: sys.modules.get(name)
    for name in (
        "config",
        "fastapi",
        "fastapi.middleware.cors",
        "fastapi.responses",
        "pydantic",
        "starlette.middleware.base",
        "starlette.requests",
    )
}


fastapi = sys.modules.setdefault("fastapi", types.ModuleType("fastapi"))


class _FastAPI:
    def __init__(self, *args, **kwargs):
        pass

    def add_middleware(self, *args, **kwargs):
        return None

    def get(self, *args, **kwargs):
        def decorator(func):
            return func

        return decorator

    def post(self, *args, **kwargs):
        def decorator(func):
            return func

        return decorator

    def exception_handler(self, *args, **kwargs):
        def decorator(func):
            return func

        return decorator

    def on_event(self, *args, **kwargs):
        def decorator(func):
            return func

        return decorator


class _HTTPException(Exception):
    def __init__(self, status_code: int, detail: str):
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


class _BackgroundTasks:
    def add_task(self, *args, **kwargs):
        return None


def _File(*args, **kwargs):
    return None


class _UploadFile:
    pass


fastapi.FastAPI = _FastAPI
fastapi.HTTPException = _HTTPException
fastapi.BackgroundTasks = _BackgroundTasks
fastapi.File = _File
fastapi.UploadFile = _UploadFile

fastapi_cors = sys.modules.setdefault("fastapi.middleware.cors", types.ModuleType("fastapi.middleware.cors"))


class _CORSMiddleware:
    def __init__(self, *args, **kwargs):
        pass


fastapi_cors.CORSMiddleware = _CORSMiddleware

fastapi_responses = sys.modules.setdefault("fastapi.responses", types.ModuleType("fastapi.responses"))


class _FileResponse:
    def __init__(self, *args, **kwargs):
        pass


class _JSONResponse:
    def __init__(self, *args, **kwargs):
        self.status_code = kwargs.get("status_code")
        self.content = kwargs.get("content")


fastapi_responses.FileResponse = _FileResponse
fastapi_responses.JSONResponse = _JSONResponse

pydantic = sys.modules.setdefault("pydantic", types.ModuleType("pydantic"))


class _BaseModel:
    def __init__(self, **data):
        for name, value in self.__class__.__dict__.items():
            if name.startswith("_") or callable(value):
                continue
            setattr(self, name, data.get(name, value))
        for name, value in data.items():
            setattr(self, name, value)


pydantic.BaseModel = _BaseModel

starlette_middleware_base = sys.modules.setdefault("starlette.middleware.base", types.ModuleType("starlette.middleware.base"))


class _BaseHTTPMiddleware:
    def __init__(self, *args, **kwargs):
        pass


starlette_middleware_base.BaseHTTPMiddleware = _BaseHTTPMiddleware

starlette_requests = sys.modules.setdefault("starlette.requests", types.ModuleType("starlette.requests"))


class _Request:
    pass


starlette_requests.Request = _Request


VOICE_DIR = Path(__file__).resolve().parents[1]
MAIN_PATH = VOICE_DIR / "main.py"
TTS_ENGINE_PATH = VOICE_DIR / "tts_engine.py"

spec = util.spec_from_file_location("voice_server_main", MAIN_PATH)
assert spec is not None and spec.loader is not None
voice_main = util.module_from_spec(spec)
try:
    spec.loader.exec_module(voice_main)

    tts_spec = util.spec_from_file_location("voice_server_tts_engine", TTS_ENGINE_PATH)
    assert tts_spec is not None and tts_spec.loader is not None
    tts_engine = util.module_from_spec(tts_spec)
    tts_spec.loader.exec_module(tts_engine)
finally:
    for name, module in _ORIGINAL_MODULES.items():
        if module is None:
            sys.modules.pop(name, None)
        else:
            sys.modules[name] = module


def test_select_tts_voice_name_prefers_requested_voice() -> None:
    assert tts_engine.select_tts_voice_name(["F1", "F2"], "F2") == "F2"
    assert tts_engine.select_tts_voice_name(["F1", "F2"], "F9") == "F1"


def test_health_is_lightweight() -> None:
    assert voice_main.health() == {"ok": True, "server": "voice"}


def test_ready_exposes_available_voice_names(monkeypatch) -> None:
    monkeypatch.setitem(voice_main._STT_RUNTIME_STATES, "fast", {"device": "cpu", "compute_type": "int8"})
    monkeypatch.setitem(voice_main._STT_RUNTIME_STATES, "accurate", {"device": "cpu", "compute_type": "int8"})
    monkeypatch.setitem(voice_main._TTS_RUNTIME_STATE, "available_voice_names", ["F1", "F2"])
    monkeypatch.setitem(voice_main._TTS_RUNTIME_STATE, "ready", True)
    monkeypatch.setitem(voice_main._TTS_RUNTIME_STATE, "error", None)
    monkeypatch.setitem(voice_main._TTS_RUNTIME_STATE, "voice_name", "F1")

    payload = voice_main.ready()
    content = payload.content

    assert payload.status_code == 200
    assert content["ready"] is True
    assert content["tts_voice_names"] == ["F1", "F2"]
