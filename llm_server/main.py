import logging
import os
import re
from threading import Lock
from typing import Any, Optional

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnableLambda
from pydantic import BaseModel, Field
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request


MOCK_MODE = os.getenv("MOCK_MODE", "false").lower() == "true"
LLM_MODEL_ID = os.getenv("LLM_MODEL_ID", "LGAI-EXAONE/EXAONE-3.5-2.4B-Instruct")
LLM_MODEL_REVISION = os.getenv("LLM_MODEL_REVISION", "c38726a")

logger = logging.getLogger("llm_server")
_MODEL_BUNDLE: Optional[dict[str, Any]] = None
_MODEL_LOCK = Lock()

app = FastAPI(title="Marimo LLM Server", version="0.1.0")
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


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled llm-server error: %s", exc)
    return JSONResponse(
        status_code=500,
        content={"detail": str(exc), "type": exc.__class__.__name__},
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Private-Network": "true",
        },
    )


class GeneratePayload(BaseModel):
    question: str
    history: list[dict[str, str]] = Field(default_factory=list)
    sensor: Optional[dict[str, Any]] = None
    state: Optional[dict[str, Any]] = None
    session_id: Optional[str] = None
    persona_memo: Optional[str] = None
    system_memo: Optional[str] = None
    use_sensor_context: bool = False


def format_context(payload: GeneratePayload) -> str:
    if not payload.use_sensor_context:
        return "센서 정보 없음"

    sensor = payload.sensor or {}
    state = payload.state or {}
    return f"센서값: {sensor}\n상태 판단: {state}"


def build_system_prompt(payload: GeneratePayload) -> str:
    persona_note = payload.persona_memo.strip() if payload.persona_memo else ""
    system_note = payload.system_memo.strip() if payload.system_memo else ""
    parts = [
        "너는 '마리모'라는 한국어 음성 비서다.",
        "답변은 자연스러운 한국어 말투로 한다.",
        "보통 1~2문장, 길어도 3문장 이내로 끝낸다.",
        "답변은 반드시 문장을 끝까지 완성하고 끝낸다.",
        "불필요한 서론, 리스트, 중복 설명은 피한다.",
        "답변 앞에 '마리모:' 같은 화자 표시는 붙이지 않는다.",
        "JSON, 키-값 나열, 표 형식, 항목 목록으로 답하지 말고 항상 자연스러운 대화 문장만 사용한다.",
        "호출어로 대화가 시작되면 바로 이어서 도와준다.",
        "이전 대화를 참고하되, 이전 문장을 그대로 복사하지 말고 현재 질문에 맞게 재구성한다.",
        "사용자가 '마리모는 어떤 식물이야?'처럼 묻는 경우에는 비서 자기소개가 아니라 실제 마리모 생물 정보로 답한다.",
        "모호하면 짧게 한 번만 다시 묻는다.",
        "같은 단어를 연속해서 쓰지 않는다.",
    ]
    if persona_note:
        parts.append(f"추가 페르소나 메모: {persona_note}")
    if system_note:
        parts.append(f"추가 시스템 메모: {system_note}")
    return "\n".join(parts)


def build_history_messages(payload: GeneratePayload) -> list[dict[str, str]]:
    messages: list[dict[str, str]] = []
    for item in payload.history[-16:]:
        role = (item.get("role") or "").strip().lower()
        content = (item.get("content") or item.get("text") or "").strip()
        if role not in {"user", "assistant", "system"}:
            continue
        if not content:
            continue
        messages.append({"role": role, "content": content})
    return messages


def direct_answer(question: str) -> Optional[str]:
    normalized = " ".join(question.strip().split())
    lowered = normalized.lower()
    if not normalized:
        return None

    if "안녕 마리모" in normalized or lowered in {"마리모", "안녕 마리모야", "마리모야"}:
        return "네, 듣고 있어요. 무엇을 도와드릴까요?"

    if any(
        token in normalized
        for token in (
            "마리모는 어떤 식물이야",
            "마리모가 뭐야",
            "마리모의 종",
            "마리모 자체",
        )
    ):
        return "마리모는 보통 구형으로 자라는 녹조류를 뜻하고, 어항에서 관상용으로 키우는 경우가 많습니다."

    return None


def normalize_answer(answer: str) -> str:
    cleaned = answer.strip()
    cleaned = re.sub(r"^(마리모|assistant)\s*[:：]\s*", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"^(사용자|user)\s*[:：]\s*", "", cleaned, flags=re.IGNORECASE)
    return cleaned.strip()


def build_mock_answer(payload: GeneratePayload) -> str:
    question = payload.question.strip()
    quick = direct_answer(question)
    if quick:
        return quick

    if not payload.use_sensor_context:
        if any(token in question for token in ("안녕", "소개", "이름")):
            return "안녕하세요. 저는 식물 상태를 부드럽게 설명해 주는 작은 한국어 음성 비서예요."
        return "좋아요. 질문을 자연스럽게 이해해서 필요한 내용을 한국어로 간단히 말해볼게요."

    sensor = payload.sensor or {}
    state = payload.state or {}
    alerts = state.get("alerts") or []
    level = state.get("level", "normal")

    values = []
    for key, label in (
        ("temperature", "기온"),
        ("humidity", "습도"),
        ("light", "조도"),
        ("water_level", "수분"),
        ("distance", "거리"),
    ):
        if sensor.get(key) is not None:
            values.append(f"{label} {sensor[key]}")

    summary = ", ".join(values) if values else "센서값이 아직 충분히 들어오지 않았어요."
    if alerts:
        return f"지금 상태는 {level} 단계예요. {summary}로 보이고 {', '.join(alerts)} 신호가 있어요."
    return f"지금 상태는 {level} 단계예요. {summary} 비교적 안정적입니다."


def get_model_bundle() -> dict[str, Any]:
    from transformers.models.auto.modeling_auto import AutoModelForCausalLM
    from transformers.models.auto.tokenization_auto import AutoTokenizer
    import torch

    global _MODEL_BUNDLE
    with _MODEL_LOCK:
        if _MODEL_BUNDLE is not None:
            return _MODEL_BUNDLE

        tokenizer = AutoTokenizer.from_pretrained(
            LLM_MODEL_ID,
            revision=LLM_MODEL_REVISION,
            trust_remote_code=True,
        )
        model = AutoModelForCausalLM.from_pretrained(
            LLM_MODEL_ID,
            revision=LLM_MODEL_REVISION,
            low_cpu_mem_usage=False,
            trust_remote_code=True,
        )

        device = "cuda" if torch.cuda.is_available() else "cpu"
        if device == "cuda":
            model = model.half()
        model = model.to(device)
        model.eval()

        _MODEL_BUNDLE = {"tokenizer": tokenizer, "model": model, "device": device}
        return _MODEL_BUNDLE


def get_readiness_state() -> dict[str, Any]:
    if MOCK_MODE:
        return {
            "ok": True,
            "ready": True,
            "mode": "mock",
            "model_loaded": True,
            "cuda_available": False,
            "device": "mock",
            "error": None,
            "error_type": None,
        }

    try:
        import torch

        bundle = get_model_bundle()
        return {
            "ok": True,
            "ready": True,
            "mode": "huggingface",
            "model_loaded": True,
            "cuda_available": torch.cuda.is_available(),
            "device": bundle["device"],
            "error": None,
            "error_type": None,
        }
    except Exception as exc:
        logger.exception("LLM readiness check failed: %s", exc)
        return {
            "ok": False,
            "ready": False,
            "mode": "huggingface",
            "model_loaded": False,
            "cuda_available": False,
            "device": None,
            "error": str(exc),
            "error_type": exc.__class__.__name__,
        }


def generate_answer(payload: GeneratePayload) -> str:
    import torch

    question = payload.question.strip()
    quick = direct_answer(question)
    if quick:
        return quick

    bundle = get_model_bundle()
    tokenizer = bundle["tokenizer"]
    model = bundle["model"]
    device = bundle["device"]

    messages = [{"role": "system", "content": build_system_prompt(payload)}]
    messages.extend(build_history_messages(payload))
    messages.append(
        {
            "role": "user",
            "content": f"사용자 질문: {question}\n\n참고 정보:\n{format_context(payload)}",
        }
    )

    prompt = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    inputs = tokenizer(prompt, return_tensors="pt").to(device)

    with torch.inference_mode():
        output_ids = model.generate(
            **inputs,
            do_sample=False,
            max_new_tokens=256,
            repetition_penalty=1.12,
            no_repeat_ngram_size=2,
            length_penalty=0.9,
            pad_token_id=tokenizer.eos_token_id,
        )

    generated_ids = output_ids[0][inputs["input_ids"].shape[-1] :]
    return normalize_answer(tokenizer.decode(generated_ids, skip_special_tokens=True))


def get_chain():
    if MOCK_MODE:
        model = RunnableLambda(lambda values: build_mock_answer(values["payload"]))
        return RunnableLambda(lambda payload: {"payload": payload}) | model | StrOutputParser()

    return RunnableLambda(generate_answer) | StrOutputParser()


@app.get("/health")
def health() -> JSONResponse:
    readiness = get_readiness_state()
    status_code = 200 if readiness["ok"] else 503
    return JSONResponse(
        status_code=status_code,
        content={
            "ok": readiness["ok"],
            "ready": readiness["ready"],
            "server": "llm",
            "mock_mode": MOCK_MODE,
            "model": LLM_MODEL_ID,
            "revision": LLM_MODEL_REVISION,
            "framework": "langchain",
            "model_loaded": readiness["model_loaded"],
            "cuda_available": readiness["cuda_available"],
            "device": readiness["device"],
            "mode": readiness["mode"],
            "error": readiness["error"],
            "error_type": readiness["error_type"],
        },
    )


@app.post("/generate")
def generate(payload: GeneratePayload) -> dict[str, Any]:
    answer = get_chain().invoke(payload)
    return {
        "answer": answer.strip(),
        "mock": MOCK_MODE,
        "framework": "langchain",
    }
