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
from config import LLM_MODEL_ID, LLM_MODEL_REVISION, MOCK_MODE, RUN_MODE, logger
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
            "model": LLM_MODEL_ID,
            "revision": LLM_MODEL_REVISION,
            "framework": "python",
            "model_loaded": readiness["model_loaded"],
            "cuda_available": readiness["cuda_available"],
            "device": readiness["device"],
            "mode": readiness["mode"],
            "error": readiness["error"],
            "error_type": readiness["error_type"],
        },
    )


@app.post("/generate")
def generate(payload: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(payload, GeneratePayload):
        payload = GeneratePayload.model_validate(payload)
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
