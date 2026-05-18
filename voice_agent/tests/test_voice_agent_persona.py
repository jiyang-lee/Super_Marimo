from importlib import util
from pathlib import Path
import sys
import types


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

if not hasattr(fastapi, "FastAPI"):
    fastapi.FastAPI = _FastAPI

class _HTTPException(Exception):
    def __init__(self, status_code: int, detail: str):
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail

if not hasattr(fastapi, "HTTPException"):
    fastapi.HTTPException = _HTTPException

fastapi_cors = sys.modules.setdefault("fastapi.middleware.cors", types.ModuleType("fastapi.middleware.cors"))

class _CORSMiddleware:
    def __init__(self, *args, **kwargs):
        pass

if not hasattr(fastapi_cors, "CORSMiddleware"):
    fastapi_cors.CORSMiddleware = _CORSMiddleware

fastapi_responses = sys.modules.setdefault("fastapi.responses", types.ModuleType("fastapi.responses"))

class _JSONResponse:
    def __init__(self, *args, **kwargs):
        pass

if not hasattr(fastapi_responses, "JSONResponse"):
    fastapi_responses.JSONResponse = _JSONResponse

starlette_middleware_base = sys.modules.setdefault("starlette.middleware.base", types.ModuleType("starlette.middleware.base"))

class _BaseHTTPMiddleware:
    def __init__(self, *args, **kwargs):
        pass

if not hasattr(starlette_middleware_base, "BaseHTTPMiddleware"):
    starlette_middleware_base.BaseHTTPMiddleware = _BaseHTTPMiddleware

starlette_requests = sys.modules.setdefault("starlette.requests", types.ModuleType("starlette.requests"))

class _Request:
    pass

if not hasattr(starlette_requests, "Request"):
    starlette_requests.Request = _Request

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
    if default_factory is not None:
        return default_factory()
    return kwargs.get("default")

pydantic.BaseModel = _BaseModel
pydantic.Field = _Field


VOICE_MAIN_PATH = Path(__file__).resolve().parents[1] / "main.py"
spec = util.spec_from_file_location("voice_agent_main", VOICE_MAIN_PATH)
assert spec is not None and spec.loader is not None
voice_main = util.module_from_spec(spec)
spec.loader.exec_module(voice_main)
voice_main.AskPayload.model_rebuild(_types_namespace=vars(voice_main))
voice_main.AskResponse.model_rebuild(_types_namespace=vars(voice_main))


def test_health_reports_api(monkeypatch) -> None:
    monkeypatch.setattr(voice_main, "load_session_id", lambda: "session-123")
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

    monkeypatch.setattr(voice_main, "load_session_id", lambda: None)
    monkeypatch.setattr(voice_main, "save_session_id", lambda session_id: saved_sessions.append(session_id))
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
            "tts_text": f"응답: {text}",
        },
    )
    monkeypatch.setattr(
        voice_main,
        "synthesize_tts",
        lambda text, voice_name=None: captured_tts_call.update({"text": text, "voice_name": voice_name})
        or f"C:/temp/{text}.wav",
    )

    payload = voice_main.AskPayload(
        text="테스트 질문",
        session_id="11111111-1111-1111-1111-111111111111",
        speak=True,
        persona_memo="한국인 꼬마 같은 말투",
        system_memo="한국어만 사용",
        voice_name="F2",
    )
    response = voice_main.ask(payload)

    assert response.saved is True
    assert response.answer == "응답: 테스트 질문"
    assert response.session_id == "11111111-1111-1111-1111-111111111111"
    assert response.tts_ok is True
    assert response.interaction_id == 7
    assert response.messages_saved == 2
    assert response.session_created is True
    assert saved_sessions[-1] == "11111111-1111-1111-1111-111111111111"
    assert captured_api_call["persona_memo"] == "한국인 꼬마 같은 말투"
    assert captured_api_call["system_memo"] == "한국어만 사용"
    assert captured_tts_call["voice_name"] == "F2"
