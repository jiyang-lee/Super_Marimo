from __future__ import annotations

import json
import logging
import os
import tempfile
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Optional

import requests
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from core.api_client import ApiClient
from core.event_poller import EventPoller
from core.session_store import SessionStore
from core.tts_client import TtsClient


API_SERVER_URL = os.getenv("API_SERVER_URL", "http://127.0.0.1:8000")
VOICE_SERVER_URL = os.getenv("VOICE_SERVER_URL", "http://127.0.0.1:8002")
LLM_SERVER_URL = os.getenv("LLM_SERVER_URL", "http://127.0.0.1:8001")
SESSION_FILE = Path(os.getenv("SESSION_FILE", "/tmp/super_marimo_voice_agent_session.json"))
DEFAULT_STT_MODEL = os.getenv("STT_MODEL", "fast")
VOICE_AGENT_PORT = int(os.getenv("VOICE_AGENT_PORT", "8003"))
SHARED_AUDIO_DIR = os.getenv("SHARED_AUDIO_DIR", "/app/shared/audio")
EVENT_POLLER_INTERVAL = float(os.getenv("EVENT_POLLER_INTERVAL", "1.0"))

logger = logging.getLogger("voice_agent")

api_client = ApiClient(API_SERVER_URL, VOICE_SERVER_URL, LLM_SERVER_URL)
session_store = SessionStore(str(SESSION_FILE))
tts_client = TtsClient(api_client, output_dir=SHARED_AUDIO_DIR)
event_poller = EventPoller(
    api_client,
    tts_client,
    interval_sec=EVENT_POLLER_INTERVAL,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Voice Agent starting...")
    event_poller.start()
    yield
    logger.info("Voice Agent shutting down...")
    event_poller.stop()


app = FastAPI(title="Super Marimo Voice Agent", version="0.3.0", lifespan=lifespan)
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
    persona_memo: Optional[str] = None
    system_memo: Optional[str] = None
    voice_name: Optional[str] = None


class AskResponse(BaseModel):
    saved: bool
    answer: str
    session_id: str
    api_health: dict[str, Any]
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


def api_health() -> dict[str, Any]:
    try:
        data = api_client.api_health()
        return {"ok": True, "data": data}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


def ask_api_server(
    text: str,
    session_id: str,
    *,
    persona_memo: Optional[str] = None,
    system_memo: Optional[str] = None,
) -> dict[str, Any]:
    return api_client.voice_ask(text, session_id, persona_memo=persona_memo, system_memo=system_memo)


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


def synthesize_tts(text: str, voice_name: Optional[str] = None) -> Optional[str]:
    try:
        path = tts_client.synthesize_to_file(text, voice_name=voice_name, prefix="ask")
        return str(path)
    except Exception as exc:
        logger.warning("TTS synthesis failed: %s", exc)
        return None


@app.get("/health")
def health() -> dict[str, Any]:
    session_id = session_store.load()
    return {
        "ok": True,
        "server": "voice-agent",
        "api_server": api_health(),
        "default_stt_model": DEFAULT_STT_MODEL,
        "session_id": session_id,
        "event_poller_running": event_poller._thread is not None and event_poller._thread.is_alive(),
    }


@app.post("/ask", response_model=AskResponse)
def ask(payload: AskPayload) -> AskResponse:
    session_id = payload.session_id or session_store.load() or str(uuid.uuid4())
    session_store.save(session_id)

    a_health = api_health()
    if not a_health.get("ok"):
        raise HTTPException(status_code=503, detail=f"api-server unavailable: {a_health.get('error')}")

    api_result = ask_api_server(
        payload.text,
        session_id,
        persona_memo=payload.persona_memo,
        system_memo=payload.system_memo,
    )
    answer = extract_answer(api_result)
    tts_path: Optional[str] = None
    tts_ok = False

    if payload.speak:
        tts_path = synthesize_tts(answer, voice_name=payload.voice_name)
        tts_ok = tts_path is not None

    resolved_session_id = str(api_result.get("session_id") or session_id)
    session_store.save(resolved_session_id)

    return AskResponse(
        saved=bool(api_result.get("saved", False)),
        answer=answer,
        session_id=resolved_session_id,
        api_health=a_health,
        tts_ok=tts_ok,
        tts_path=tts_path,
        interaction_id=api_result.get("interaction_id"),
        session_created=api_result.get("session_created"),
        messages_saved=api_result.get("messages_saved"),
    )


def main() -> None:
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=VOICE_AGENT_PORT, reload=False)


if __name__ == "__main__":
    main()
