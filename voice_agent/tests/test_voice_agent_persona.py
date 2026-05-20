import sys
import types
from importlib import util
from pathlib import Path


_ORIGINAL_MODULES = {
    name: sys.modules.get(name)
    for name in (
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


class _BackgroundTasks:
    def __init__(self):
        self.tasks = []

    def add_task(self, func, *args, **kwargs):
        self.tasks.append((func, args, kwargs))
        return None


class _HTTPException(Exception):
    def __init__(self, status_code: int, detail: str):
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


fastapi.FastAPI = _FastAPI
fastapi.HTTPException = _HTTPException
fastapi.BackgroundTasks = _BackgroundTasks

fastapi_cors = sys.modules.setdefault("fastapi.middleware.cors", types.ModuleType("fastapi.middleware.cors"))


class _CORSMiddleware:
    def __init__(self, *args, **kwargs):
        pass


fastapi_cors.CORSMiddleware = _CORSMiddleware

fastapi_responses = sys.modules.setdefault("fastapi.responses", types.ModuleType("fastapi.responses"))


class _JSONResponse:
    def __init__(self, *args, **kwargs):
        self.status_code = kwargs.get("status_code")
        self.content = kwargs.get("content")


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

    @classmethod
    def model_rebuild(cls, *args, **kwargs):
        return None


def _Field(*args, **kwargs):
    default_factory = kwargs.get("default_factory")
    return default_factory() if default_factory is not None else kwargs.get("default")


pydantic.BaseModel = _BaseModel
pydantic.Field = _Field

starlette_middleware_base = sys.modules.setdefault("starlette.middleware.base", types.ModuleType("starlette.middleware.base"))


class _BaseHTTPMiddleware:
    def __init__(self, *args, **kwargs):
        pass


starlette_middleware_base.BaseHTTPMiddleware = _BaseHTTPMiddleware

starlette_requests = sys.modules.setdefault("starlette.requests", types.ModuleType("starlette.requests"))


class _Request:
    pass


starlette_requests.Request = _Request


VOICE_MAIN_PATH = Path(__file__).resolve().parents[1] / "main.py"
spec = util.spec_from_file_location("voice_agent_main", VOICE_MAIN_PATH)
assert spec is not None and spec.loader is not None
voice_main = util.module_from_spec(spec)
try:
    spec.loader.exec_module(voice_main)
finally:
    for name, module in _ORIGINAL_MODULES.items():
        if module is None:
            sys.modules.pop(name, None)
        else:
            sys.modules[name] = module


def test_health_reports_api(monkeypatch) -> None:
    monkeypatch.setattr(voice_main.session_store, "load", lambda: "session-123")
    monkeypatch.setattr(voice_main, "api_health", lambda: {"ok": True, "data": {"ok": True}})

    payload = voice_main.health()

    assert payload["ok"] is True
    assert payload["server"] == "voice-agent"
    assert payload["session_id"] == "session-123"
    assert payload["api_server"]["ok"] is True


def test_ask_routes_through_api_server(monkeypatch) -> None:
    saved_sessions: list[str] = []
    captured_api_call: dict[str, object] = {}
    captured_tts_call: dict[str, object] = {}

    monkeypatch.setattr(voice_main.session_store, "load", lambda: None)
    monkeypatch.setattr(voice_main.session_store, "save", lambda session_id: saved_sessions.append(session_id))
    monkeypatch.setattr(voice_main, "api_health", lambda: {"ok": True, "data": {"ok": True}})
    monkeypatch.setattr(
        voice_main,
        "ask_api_server",
        lambda text, session_id, persona_memo=None, system_memo=None: captured_api_call.update(
            {
                "text": text,
                "session_id": session_id,
                "persona_memo": persona_memo,
                "system_memo": system_memo,
            }
        )
        or {
            "saved": True,
            "session_id": session_id,
            "interaction_id": 7,
            "session_created": True,
            "messages_saved": 2,
            "llm_answer": f"answer: {text}",
            "tts_text": f"sound: {text}",
        },
    )
    monkeypatch.setattr(
        voice_main,
        "synthesize_tts",
        lambda text, voice_name=None: captured_tts_call.update({"text": text, "voice_name": voice_name})
        or f"C:/temp/{text}.wav",
    )

    payload = voice_main.AskPayload(
        text="test question",
        session_id="11111111-1111-1111-1111-111111111111",
        speak=True,
        persona_memo="persona memo",
        system_memo="system memo",
        voice_name="F2",
    )
    response = voice_main.ask(payload)

    assert response.saved is True
    assert response.answer == "answer: test question"
    assert response.session_id == "11111111-1111-1111-1111-111111111111"
    assert response.tts_ok is True
    assert response.interaction_id == 7
    assert response.messages_saved == 2
    assert response.session_created is True
    assert saved_sessions[-1] == "11111111-1111-1111-1111-111111111111"
    assert captured_api_call["persona_memo"] == "persona memo"
    assert captured_api_call["system_memo"] == "system memo"
    assert captured_tts_call["text"] == "sound: test question"
    assert captured_tts_call["voice_name"] == "F2"
