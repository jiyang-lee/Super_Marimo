import sys
from pathlib import Path
from typing import Any

CURRENT_DIR = Path(__file__).resolve().parent
if str(CURRENT_DIR) not in sys.path:
    sys.path.insert(0, str(CURRENT_DIR))
if "config" in sys.modules:
    del sys.modules["config"]

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from chain_builder import get_chain
from config import (
    HF_LLM_BACKEND,
    HF_LLM_ENDPOINT_URL,
    HF_LLM_ROUTER_BASE_URL,
    HF_LLM_ROUTER_MODEL,
    HF_TIMEOUT_SEC,
    HF_TOKEN,
    LLM_MODEL_ID,
    LLM_MODEL_REVISION,
    MOCK_MODE,
    RUN_MODE,
    logger,
)
from hf_endpoint_client import HF_LLM_RUNTIME_STATE, chat_completion, post_json
from model_engine import get_readiness_state


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
    sensor: dict[str, Any] | None = None
    state: dict[str, Any] | None = None
    runtime_settings: dict[str, Any] | None = None
    session_id: str | None = None
    session_summary: str | None = None
    action_result: dict[str, Any] | None = None
    persona_memo: str | None = None
    system_memo: str | None = None
    use_sensor_context: bool = False
    trigger_source: str | None = None


if hasattr(GeneratePayload, "model_rebuild"):
    GeneratePayload.model_rebuild()


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


@app.get("/health")
def health() -> JSONResponse:
    return JSONResponse(
        status_code=200,
        content={"ok": True, "server": "llm"},
    )


@app.get("/")
def root() -> JSONResponse:
    return JSONResponse(
        status_code=200,
        content={
            "ok": True,
            "server": "llm",
            "endpoints": ["/health", "/ready", "/generate"],
        },
    )


@app.get("/favicon.ico")
def favicon() -> JSONResponse:
    return JSONResponse(status_code=204, content={})


@app.get("/ready")
def ready() -> JSONResponse:
    readiness = get_readiness_state()
    status_code = 200 if readiness["ok"] else 503
    return JSONResponse(
        status_code=status_code,
        content={
            "ok": readiness["ok"],
            "ready": readiness["ready"],
            "server": "llm",
            "run_mode": RUN_MODE,
            "mock_mode": MOCK_MODE,
            "backend": "mock" if MOCK_MODE else ("hf_router" if HF_LLM_BACKEND == "router" else ("hf_endpoint" if HF_LLM_ENDPOINT_URL else "local")),
            "hf_llm_backend": HF_LLM_BACKEND,
            "hf_llm_endpoint_configured": bool(HF_LLM_ENDPOINT_URL),
            "hf_llm_router_model": HF_LLM_ROUTER_MODEL,
            "hf_token_configured": bool(HF_TOKEN),
            "model": LLM_MODEL_ID,
            "revision": LLM_MODEL_REVISION,
            "framework": "python",
            "model_loaded": readiness["model_loaded"],
            "cuda_available": readiness["cuda_available"],
            "device": readiness["device"],
            "mode": readiness["mode"],
            "error": readiness["error"],
            "error_type": readiness["error_type"],
            "last_latency_ms": readiness.get("last_latency_ms"),
        },
    )


@app.post("/generate")
def generate(payload: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(payload, GeneratePayload):
        payload = GeneratePayload.model_validate(payload) if hasattr(GeneratePayload, "model_validate") else GeneratePayload.parse_obj(payload)
    contract = get_chain().invoke(payload)
    if not isinstance(contract, dict):
        contract = {
            "answer": str(contract or "").strip(),
            "action_proposal": None,
            "confidence": 0.0,
            "reason": "chain_returned_non_dict",
        }
    contract.setdefault("answer", "")
    contract.setdefault("action_proposal", None)
    contract.setdefault("confidence", 0.0)
    contract.setdefault("reason", "")
    contract["mock"] = MOCK_MODE
    contract["framework"] = "python"
    return contract


@app.on_event("startup")
def startup_warm_hf_endpoint() -> None:
    if MOCK_MODE:
        return
    try:
        if HF_LLM_BACKEND == "router" and HF_TOKEN:
            _, latency_ms = chat_completion(
                base_url=HF_LLM_ROUTER_BASE_URL,
                api_key=HF_TOKEN,
                model=HF_LLM_ROUTER_MODEL,
                messages=[{"role": "user", "content": "ping"}],
                max_tokens=1,
                timeout=HF_TIMEOUT_SEC,
            )
            HF_LLM_RUNTIME_STATE.update({"ready": True, "backend": "router", "model": HF_LLM_ROUTER_MODEL, "last_latency_ms": latency_ms, "last_error": None})
            return
        if not HF_LLM_ENDPOINT_URL:
            return
        _, latency_ms = post_json(
            HF_LLM_ENDPOINT_URL,
            {
                "messages": [{"role": "user", "content": "ping"}],
                "inputs": "ping",
                "parameters": {"max_new_tokens": 1, "temperature": 0.0, "do_sample": False},
            },
            token=HF_TOKEN,
            timeout=HF_TIMEOUT_SEC,
        )
        HF_LLM_RUNTIME_STATE.update({"ready": True, "backend": "endpoint", "model": LLM_MODEL_ID, "last_latency_ms": latency_ms, "last_error": None})
    except Exception as exc:
        HF_LLM_RUNTIME_STATE.update({"ready": False, "last_error": str(exc)})
        logger.warning("HF LLM warmup failed: %s", exc)
