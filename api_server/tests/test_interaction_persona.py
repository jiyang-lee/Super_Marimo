import asyncio
import sys
import types


fastapi = sys.modules.setdefault("fastapi", types.ModuleType("fastapi"))

class _HTTPException(Exception):
    def __init__(self, status_code: int, detail: str):
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail

if not hasattr(fastapi, "HTTPException"):
    fastapi.HTTPException = _HTTPException

if not hasattr(fastapi, "FastAPI"):
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

    fastapi.FastAPI = _FastAPI

fastapi_cors = sys.modules.setdefault("fastapi.middleware.cors", types.ModuleType("fastapi.middleware.cors"))
if not hasattr(fastapi_cors, "CORSMiddleware"):
    class _CORSMiddleware:
        def __init__(self, *args, **kwargs):
            pass

    fastapi_cors.CORSMiddleware = _CORSMiddleware

fastapi_responses = sys.modules.setdefault("fastapi.responses", types.ModuleType("fastapi.responses"))
if not hasattr(fastapi_responses, "JSONResponse"):
    class _JSONResponse:
        def __init__(self, *args, **kwargs):
            pass

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

    def model_dump(self):
        return {key: value for key, value in self.__dict__.items() if not key.startswith("_")}

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

httpx = sys.modules.setdefault("httpx", types.ModuleType("httpx"))
if not hasattr(httpx, "HTTPError"):
    class _HTTPError(Exception):
        pass

    httpx.HTTPError = _HTTPError
if not hasattr(httpx, "AsyncClient"):
    class _AsyncClient:
        def __init__(self, *args, **kwargs):
            pass

    httpx.AsyncClient = _AsyncClient

psycopg = sys.modules.setdefault("psycopg", types.ModuleType("psycopg"))
if not hasattr(psycopg, "connect"):
    def _connect(*args, **kwargs):
        raise RuntimeError("connect not available in test")

    psycopg.connect = _connect

psycopg_rows = sys.modules.setdefault("psycopg.rows", types.ModuleType("psycopg.rows"))
if not hasattr(psycopg_rows, "dict_row"):
    psycopg_rows.dict_row = object()

sys.modules.setdefault("psycopg.types", types.ModuleType("psycopg.types"))
psycopg_json = sys.modules.setdefault("psycopg.types.json", types.ModuleType("psycopg.types.json"))
if not hasattr(psycopg_json, "Json"):
    class _Json:
        def __init__(self, value):
            self.value = value

    psycopg_json.Json = _Json


from services import interaction_service


class _DummyResponse:
    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict[str, str]:
        return {"answer": "ok"}


class _DummyClient:
    def __init__(self) -> None:
        self.url: str | None = None
        self.payload: dict[str, object] | None = None

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def post(self, url: str, json: dict[str, object]):
        self.url = url
        self.payload = json
        return _DummyResponse()


def test_request_llm_includes_persona_and_system_memo(monkeypatch) -> None:
    client = _DummyClient()
    monkeypatch.setattr(interaction_service.httpx, "AsyncClient", lambda timeout: client)

    result = asyncio.run(
        interaction_service.request_llm(
            "지금 뭐해?",
            sensor=None,
            state={"level": "chat"},
            use_sensor_context=False,
            history=[],
            persona_memo="한국인 꼬마 같은 말투",
            system_memo="짧고 자연스럽게",
        )
    )

    assert result["answer"] == "ok"
    assert client.url == "http://llm-server:8000/generate"
    assert client.payload is not None
    assert client.payload["persona_memo"] == "한국인 꼬마 같은 말투"
    assert client.payload["system_memo"] == "짧고 자연스럽게"
