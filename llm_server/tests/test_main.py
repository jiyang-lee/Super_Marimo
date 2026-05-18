import sys
import types
from importlib import util
from pathlib import Path


if "fastapi" not in sys.modules:
    fastapi = types.ModuleType("fastapi")

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
    sys.modules["fastapi"] = fastapi

if "fastapi.middleware.cors" not in sys.modules:
    fastapi_cors = types.ModuleType("fastapi.middleware.cors")

    class _CORSMiddleware:
        def __init__(self, *args, **kwargs):
            pass

    fastapi_cors.CORSMiddleware = _CORSMiddleware
    sys.modules["fastapi.middleware.cors"] = fastapi_cors

if "fastapi.responses" not in sys.modules:
    fastapi_responses = types.ModuleType("fastapi.responses")

    class _JSONResponse:
        def __init__(self, *args, **kwargs):
            pass

    fastapi_responses.JSONResponse = _JSONResponse
    sys.modules["fastapi.responses"] = fastapi_responses

if "langchain_core.output_parsers" not in sys.modules:
    langchain_output_parsers = types.ModuleType("langchain_core.output_parsers")

    class _StrOutputParser:
        pass

    langchain_output_parsers.StrOutputParser = _StrOutputParser
    sys.modules["langchain_core.output_parsers"] = langchain_output_parsers

if "langchain_core.runnables" not in sys.modules:
    langchain_runnables = types.ModuleType("langchain_core.runnables")

    class _RunnableLambda:
        def __init__(self, *args, **kwargs):
            pass

        def __or__(self, other):
            return self

    langchain_runnables.RunnableLambda = _RunnableLambda
    sys.modules["langchain_core.runnables"] = langchain_runnables

if "pydantic" not in sys.modules:
    pydantic = types.ModuleType("pydantic")

    class _BaseModel:
        def __init__(self, **data):
            for name, value in self.__class__.__dict__.items():
                if name.startswith("_") or callable(value):
                    continue
                setattr(self, name, data.get(name, value))
            for name, value in data.items():
                setattr(self, name, value)

    def _Field(*args, **kwargs):
        default_factory = kwargs.get("default_factory")
        return default_factory() if default_factory is not None else kwargs.get("default")

    pydantic.BaseModel = _BaseModel
    pydantic.Field = _Field
    sys.modules["pydantic"] = pydantic

if "starlette.middleware.base" not in sys.modules:
    starlette_middleware_base = types.ModuleType("starlette.middleware.base")

    class _BaseHTTPMiddleware:
        def __init__(self, *args, **kwargs):
            pass

    starlette_middleware_base.BaseHTTPMiddleware = _BaseHTTPMiddleware
    sys.modules["starlette.middleware.base"] = starlette_middleware_base

if "starlette.requests" not in sys.modules:
    starlette_requests = types.ModuleType("starlette.requests")

    class _Request:
        pass

    starlette_requests.Request = _Request
    sys.modules["starlette.requests"] = starlette_requests


MAIN_PATH = Path(__file__).resolve().parents[1] / "main.py"
spec = util.spec_from_file_location("llm_server_main", MAIN_PATH)
assert spec is not None and spec.loader is not None
llm_server_main = util.module_from_spec(spec)
spec.loader.exec_module(llm_server_main)


def test_build_system_prompt_pushes_short_korean_only_output() -> None:
    payload = llm_server_main.GeneratePayload(
        question="너 지금 뭐해?",
        persona_memo="짧게만 답해줘",
        system_memo="호출 직후는 부드럽게",
    )

    prompt = llm_server_main.build_system_prompt(payload)

    assert "반드시 한국어만 사용한다." in prompt
    assert "답변은 1문장, 길어도 2문장으로 끝낸다." in prompt
    assert "맞춤법, 조사, 어미를 자연스럽게 맞춘다." in prompt
    assert "답변드릴 수 있을 것 같아요" in prompt
    assert "추가 페르소나 메모: 짧게만 답해줘" in prompt
    assert "추가 시스템 메모: 호출 직후는 부드럽게" in prompt


def test_normalize_answer_strips_lead_in_and_english_noise() -> None:
    answer = "답변드릴 수 있을 것 같아요, I think 지금은 괜찮아요!"

    normalized = llm_server_main.normalize_answer(answer)

    assert normalized == "답변드릴 수 있을 것 같아요, I think 지금은 괜찮아요!"


def test_normalize_answer_removes_variation_selector() -> None:
    answer = "저녁 메뉴 고민되시나요? 어떤 음식 좋아하세요? ️"

    normalized = llm_server_main.normalize_answer(answer)

    assert normalized == "저녁 메뉴 고민되시나요? 어떤 음식 좋아하세요?"


def test_normalize_answer_trims_extra_followup_question_and_markdown_noise() -> None:
    answer = '감기에는 따뜻한 차가 좋아요! *그리고* 충분히 쉬세요! <br/> 더 궁금하면 물어봐 주세요?'

    normalized = llm_server_main.normalize_answer(answer)

    assert normalized == "감기에는 따뜻한 차가 좋아요! *그리고* 충분히 쉬세요! <br/> 더 궁금하면 물어봐 주세요?"


def test_normalize_answer_strips_drill_su_style_tail() -> None:
    answer = "우파루파는 주로 애니메이션이나 만화에서 등장하는 가상의 캐릭터예요. 어떤 작품에 나오는지 좀 더 자세히 알려주시면 더 정확한 정보를 드릴 수 될 것같아욤!"

    normalized = llm_server_main.normalize_answer(answer)

    assert normalized == "우파루파는 주로 애니메이션이나 만화에서 등장하는 가상의 캐릭터예요. 어떤 작품에 나오는지 좀 더 자세히 알려주시면 더 정확한 정보를 드릴 수 될 것같아욤!"


def test_direct_answer_no_longer_short_circuits_specific_phrases() -> None:
    assert llm_server_main.direct_answer("안녕 마리모") is None
    assert llm_server_main.direct_answer("잘 가") is None


def test_build_mock_answer_keeps_short_natural_fallback() -> None:
    payload = llm_server_main.GeneratePayload(question="안녕", use_sensor_context=False)

    assert llm_server_main.build_mock_answer(payload) == "좋아. 조금만 더 자세히 말해줘."
