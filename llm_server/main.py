from __future__ import annotations

import logging
import os
import re
import unicodedata
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


class GeneratePayload(BaseModel):
    question: str
    history: list[dict[str, str]] = Field(default_factory=list)
    sensor: Optional[dict[str, Any]] = None
    state: Optional[dict[str, Any]] = None
    session_id: Optional[str] = None
    persona_memo: Optional[str] = None
    system_memo: Optional[str] = None
    use_sensor_context: bool = False


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


def format_context(payload: GeneratePayload) -> str:
    if not payload.use_sensor_context:
        return "센서 정보 없음"

    sensor = payload.sensor or {}
    state = payload.state or {}
    return f"센서: {sensor}\n상태: {state}"


def build_system_prompt(payload: GeneratePayload) -> str:
    persona_note = payload.persona_memo.strip() if payload.persona_memo else ""
    system_note = payload.system_memo.strip() if payload.system_memo else ""
    if not persona_note:
        persona_note = "한국인 꼬마 같은 말투를 쓰되 예의 바르고 다정하게 말한다. 짧고 자연스럽게 답하고, 너무 유치하지 않게 부드러운 톤을 유지한다."
    parts = [
        "너는 마리모라는 한국어 음성 비서다.",
        "반드시 한국어만 사용한다.",
        "영어, 로마자, 이모지, 과한 자기소개, 장황한 설명은 쓰지 않는다.",
        "답변은 1문장, 길어도 2문장으로 끝낸다.",
        "문장 끝에 추가 질문을 붙이지 말고, 필요한 정보만 말한다.",
        "질문이 모호해도 실제 질문처럼 보이면 먼저 짧게 답한다.",
        "정말 정보가 부족할 때만 한 번만 짧게 되묻는다.",
        "재질문보다 자연스러운 추론 응답을 우선한다.",
        "답변드릴 수 있을 것 같아요, 제 생각에는, I think 같은 말투는 쓰지 않는다.",
        "맞춤법, 조사, 어미를 자연스럽게 맞춘다.",
        "비문, 번역투, 어색한 높임말, 어색한 받침 처리, 이상한 조사 반복은 쓰지 않는다.",
        "별표, 괄호, 코드블록, HTML 조각, 이모지, 특수 기호는 쓰지 않는다.",
        "호출어 이후 대화는 부드럽고 친근한 톤으로 이어 간다.",
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
    if not normalized:
        return None
    return None


def normalize_answer(answer: str) -> str:
    cleaned = unicodedata.normalize("NFKC", answer or "")
    cleaned = re.sub(r"[\u200b-\u200d\ufeff\ufe0e\ufe0f]", "", cleaned)
    cleaned = re.sub(r"[\x00-\x1f\x7f]", "", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned.strip()


def build_mock_answer(payload: GeneratePayload) -> str:
    if not payload.use_sensor_context:
        return "좋아. 조금만 더 자세히 말해줘."

    sensor = payload.sensor or {}
    state = payload.state or {}
    alerts = state.get("alerts") or []
    level = state.get("level", "normal")

    values = []
    for key, label in (
        ("temperature", "기온"),
        ("humidity", "습도"),
        ("light", "조도"),
        ("water_level", "수위"),
        ("distance", "거리"),
    ):
        if sensor.get(key) is not None:
            values.append(f"{label} {sensor[key]}")

    summary = ", ".join(values) if values else "센서 값이 아직 들어오지 않았어요."
    if alerts:
        return f"지금 상태는 {level}예요. {summary}. {', '.join(alerts)}가 보여요."
    return f"지금 상태는 {level}예요. {summary}. 비교적 안정적이에요."


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
            max_new_tokens=96,
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
