from __future__ import annotations

import json
import logging
import os
import tempfile
import uuid
from pathlib import Path
from typing import Any, Optional

import requests
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request


API_SERVER_URL = os.getenv("API_SERVER_URL", "http://127.0.0.1:8000")
VOICE_SERVER_URL = os.getenv("VOICE_SERVER_URL", "http://127.0.0.1:8002")
LLM_SERVER_URL = os.getenv("LLM_SERVER_URL", "http://127.0.0.1:8001")
SESSION_FILE = Path(os.getenv("SESSION_FILE", "voice_agent.session.json"))
DEFAULT_STT_MODEL = os.getenv("STT_MODEL", "fast")

logger = logging.getLogger("voice_agent")
app = FastAPI(title="Super Marimo Voice Agent", version="0.2.0")
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


class AskPayload(BaseModel):
    text: str
    history: list[dict[str, str]] = Field(default_factory=list)
    session_id: Optional[str] = None
    speak: bool = False


class AskResponse(BaseModel):
    saved: bool
    answer: str
    session_id: str
    api_health: dict[str, Any]
    voice_health: dict[str, Any]
    llm_health: dict[str, Any]
    tts_ok: bool
    tts_path: Optional[str] = None
    interaction_id: Optional[int] = None
    session_created: Optional[bool] = None
    messages_saved: Optional[int] = None


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled voice-agent error: %s", exc)
    return JSONResponse(
        status_code=500,
        content={"detail": str(exc), "type": exc.__class__.__name__},
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Private-Network": "true",
        },
    )


def load_session_id() -> Optional[str]:
    try:
        if not SESSION_FILE.exists():
            return None
        payload = json.loads(SESSION_FILE.read_text(encoding="utf-8"))
        session_id = str(payload.get("session_id", "")).strip()
        return session_id or None
    except Exception:
        return None


def save_session_id(session_id: str) -> None:
    SESSION_FILE.parent.mkdir(parents=True, exist_ok=True)
    SESSION_FILE.write_text(
        json.dumps({"session_id": session_id}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def get_json(url: str, timeout: int = 10) -> dict[str, Any]:
    response = requests.get(url, timeout=timeout)
    response.raise_for_status()
    return response.json()


def post_json(url: str, payload: dict[str, Any], timeout: int = 120) -> dict[str, Any]:
    response = requests.post(url, json=payload, timeout=timeout)
    response.raise_for_status()
    return response.json()


def api_health() -> dict[str, Any]:
    try:
        data = get_json(f"{API_SERVER_URL}/health")
        return {"ok": True, "data": data}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


def voice_health() -> dict[str, Any]:
    try:
        data = get_json(f"{VOICE_SERVER_URL}/health")
        return {"ok": True, "data": data}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


def llm_health() -> dict[str, Any]:
    try:
        data = get_json(f"{LLM_SERVER_URL}/health")
        return {"ok": True, "data": data}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


def ask_api_server(text: str, session_id: str) -> dict[str, Any]:
    payload = {
        "text": text,
        "session_id": session_id,
        "use_sensor_context": False,
    }
    return post_json(f"{API_SERVER_URL}/voice/ask", payload, timeout=120)


def extract_answer(api_result: dict[str, Any]) -> str:
    answer = str(
        api_result.get("tts_text")
        or api_result.get("llm_answer")
        or api_result.get("answer")
        or ""
    ).strip()
    if not answer:
        raise HTTPException(status_code=502, detail="api-server returned an empty answer")
    return answer


def synthesize_tts(text: str) -> Optional[str]:
    response = requests.post(
        f"{VOICE_SERVER_URL}/tts",
        json={"text": text},
        timeout=120,
    )
    response.raise_for_status()
    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
        tmp.write(response.content)
        tts_path = tmp.name

    if os.name == "nt":
        import winsound

        winsound.PlaySound(tts_path, winsound.SND_FILENAME)

    return tts_path


@app.get("/health")
def health() -> dict[str, Any]:
    session_id = load_session_id()
    return {
        "ok": True,
        "server": "voice-agent",
        "api_server": api_health(),
        "voice_server": voice_health(),
        "llm_server": llm_health(),
        "default_stt_model": DEFAULT_STT_MODEL,
        "session_id": session_id,
    }


@app.post("/ask", response_model=AskResponse)
def ask(payload: AskPayload) -> AskResponse:
    session_id = payload.session_id or load_session_id() or str(uuid.uuid4())
    save_session_id(session_id)

    a_health = api_health()
    v_health = voice_health()
    l_health = llm_health()
    if not a_health.get("ok"):
        raise HTTPException(status_code=503, detail=f"api-server unavailable: {a_health.get('error')}")
    if not v_health.get("ok"):
        raise HTTPException(status_code=503, detail=f"voice-server unavailable: {v_health.get('error')}")
    if not l_health.get("ok"):
        raise HTTPException(status_code=503, detail=f"llm-server unavailable: {l_health.get('error')}")

    api_result = ask_api_server(payload.text, session_id)
    answer = extract_answer(api_result)
    tts_path: Optional[str] = None
    tts_ok = False

    if payload.speak:
        try:
            tts_path = synthesize_tts(answer)
            tts_ok = True
        except Exception as exc:
            logger.warning("Audio playback skipped: %s", exc)

    resolved_session_id = str(api_result.get("session_id") or session_id)
    save_session_id(resolved_session_id)

    return AskResponse(
        saved=bool(api_result.get("saved", False)),
        answer=answer,
        session_id=resolved_session_id,
        api_health=a_health,
        voice_health=v_health,
        llm_health=l_health,
        tts_ok=tts_ok,
        tts_path=tts_path,
        interaction_id=api_result.get("interaction_id"),
        session_created=api_result.get("session_created"),
        messages_saved=api_result.get("messages_saved"),
    )


def main() -> None:
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000, reload=False)


if __name__ == "__main__":
    main()
