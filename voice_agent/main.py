from __future__ import annotations

import json
import logging
import os
import tempfile
import uuid
import re
import sys
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Optional

import requests
from fastapi import BackgroundTasks, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

CURRENT_DIR = Path(__file__).resolve().parent
if str(CURRENT_DIR) not in sys.path:
    sys.path.insert(0, str(CURRENT_DIR))

from core.api_client import ApiClient
from core.event_poller import EventPoller
from core.session_store import SessionStore
from core.tts_client import TtsClient


# Service URLs: default to host loopback for local dev.
# In Docker containers these are overridden via env_file (.env.gpu / .env.mock etc).
API_SERVER_URL = os.getenv("API_SERVER_URL", "http://127.0.0.1:8000")
VOICE_SERVER_URL = os.getenv("VOICE_SERVER_URL", "http://127.0.0.1:8002")
LLM_SERVER_URL = os.getenv("LLM_SERVER_URL", "http://127.0.0.1:8001")
SESSION_FILE = Path(os.getenv("SESSION_FILE", "/tmp/super_marimo_voice_agent_session.json"))
DEFAULT_STT_MODEL = os.getenv("STT_MODEL", "fast")
VOICE_AGENT_PORT = int(os.getenv("VOICE_AGENT_PORT", "8003"))
SHARED_AUDIO_DIR = os.getenv("SHARED_AUDIO_DIR", "shared/audio")
EVENT_POLLER_INTERVAL = float(os.getenv("EVENT_POLLER_INTERVAL", "1.0"))

logger = logging.getLogger("voice_agent")

api_client = ApiClient(API_SERVER_URL, VOICE_SERVER_URL, LLM_SERVER_URL)
session_store = SessionStore(str(SESSION_FILE))
tts_client = TtsClient(api_client, output_dir=SHARED_AUDIO_DIR)
event_poller = EventPoller(
    api_client,
    tts_client,
    interval_sec=EVENT_POLLER_INTERVAL,
    event_types=["proactive_greeting"],
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
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
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
    tts_queued: bool = False
    tts_path: Optional[str] = None
    interaction_id: Optional[int] = None
    session_created: Optional[bool] = None
    messages_saved: Optional[int] = None


class SpeakPayload(BaseModel):
    text: str
    session_id: Optional[str] = None
    voice_name: Optional[str] = None
    save_message: bool = True


class SpeakResponse(BaseModel):
    saved: bool
    tts_ok: bool
    tts_queued: bool = False
    tts_path: Optional[str] = None
    session_id: str
    message_saved: bool = False


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
        return {"ok": False, "error": f"api-server unreachable: {exc}", "action": "check api-server logs: docker logs super-marimo-api-server"}


def ask_api_server(
    text: str,
    session_id: str,
    *,
    persona_memo: Optional[str] = None,
    system_memo: Optional[str] = None,
) -> dict[str, Any]:
    try:
        return api_client.voice_ask(
            text,
            session_id,
            persona_memo=persona_memo,
            system_memo=system_memo,
            use_sensor_context=True,
            session_kind="voice",
        )
    except requests.HTTPError as exc:
        logger.error("[ask] api-server returned HTTP error: %s | url=%s | status=%s", exc, exc.request.url if exc.request else "N/A", exc.response.status_code if exc.response else "N/A")
        raise HTTPException(status_code=502, detail=f"api-server error: {exc}") from exc
    except requests.RequestException as exc:
        logger.error("[ask] api-server unreachable: %s | url=%s", exc, getattr(exc, 'request', None) and getattr(exc.request, 'url', None) or "N/A")
        raise HTTPException(status_code=503, detail=f"api-server unreachable: {exc}") from exc


_SPOKEN_TEXT_KEYS = ("answer", "tts_text", "llm_answer", "response", "text", "content")


def _unwrap_spoken_text(text: str) -> str:
    cleaned = str(text or "").strip()
    if not cleaned:
        return ""

    cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", cleaned, flags=re.IGNORECASE | re.DOTALL).strip()
    json_start = cleaned.find("{")
    json_end = cleaned.rfind("}")
    if json_start != -1:
        json_blob = cleaned[json_start : json_end + 1] if json_end > json_start else cleaned[json_start:]
        try:
            parsed = json.loads(json_blob)
        except json.JSONDecodeError:
            parsed = None
        if isinstance(parsed, dict):
            for key in _SPOKEN_TEXT_KEYS:
                value = parsed.get(key)
                if isinstance(value, str) and value.strip():
                    return value.strip()
            for key in _SPOKEN_TEXT_KEYS:
                value = parsed.get(key)
                if value not in (None, ""):
                    return str(value).strip()

    return cleaned


def extract_answer(api_result: dict[str, Any]) -> str:
    answer = _unwrap_spoken_text(
        api_result.get("llm_answer")
        or api_result.get("answer")
        or api_result.get("tts_text")
        or ""
    )
    if not answer:
        raise HTTPException(status_code=502, detail="api-server returned an empty answer")
    return answer


def extract_tts_text(api_result: dict[str, Any]) -> str:
    text = _unwrap_spoken_text(
        api_result.get("tts_text")
        or api_result.get("llm_answer")
        or api_result.get("answer")
        or ""
    )
    if not text:
        raise HTTPException(status_code=502, detail="api-server returned an empty tts text")
    return text


def _resolve_session_id(explicit_session_id: Optional[str]) -> str:
    if explicit_session_id:
        return explicit_session_id

    stored_session_id = session_store.load()
    if not stored_session_id:
        return str(uuid.uuid4())

    try:
        payload = api_client.get_json(f"{API_SERVER_URL}/sessions/{stored_session_id}", timeout=10)
        session = payload.get("session") or {}
        if session.get("ended_at"):
            session_store.clear()
            return str(uuid.uuid4())
    except Exception:
        return stored_session_id

    return stored_session_id


def synthesize_tts(text: str, voice_name: Optional[str] = None, prefix: str = "ask") -> Optional[str]:
    try:
        path = tts_client.synthesize_to_file(text, voice_name=voice_name, prefix=prefix)
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
def ask(payload: AskPayload, background_tasks: BackgroundTasks = None) -> AskResponse:
    session_id = _resolve_session_id(payload.session_id)
    session_store.save(session_id)

    a_health = api_health()
    if not a_health.get("ok"):
        logger.error("[ask] api-server unavailable: %s", a_health.get("error"))
        raise HTTPException(status_code=503, detail=f"api-server unavailable: {a_health.get('error')}")

    try:
        api_result = ask_api_server(
            payload.text,
            session_id,
            persona_memo=payload.persona_memo,
            system_memo=payload.system_memo,
        )
    except HTTPException as exc:
        logger.error("[ask] voice interaction failed: %s | session_id=%s | text=%s", exc.detail, session_id, payload.text)
        raise
    except Exception as exc:
        logger.error("[ask] unexpected error in voice interaction: %s | session_id=%s", exc, session_id)
        raise HTTPException(status_code=500, detail="Unexpected error in voice interaction") from exc
    
    answer = extract_answer(api_result)
    tts_text = extract_tts_text(api_result)
    tts_path: Optional[str] = None
    tts_ok = False
    tts_queued = False

    if payload.speak:
        if background_tasks is not None:
            background_tasks.add_task(synthesize_tts, tts_text, payload.voice_name, "ask")
            tts_queued = True
            tts_ok = True
        else:
            tts_path = synthesize_tts(tts_text, voice_name=payload.voice_name)
            tts_ok = tts_path is not None
            if not tts_ok:
                logger.warning("[ask] TTS synthesis failed for answer: %s | session_id=%s", tts_text[:100], session_id)

    resolved_session_id = str(api_result.get("session_id") or session_id)
    session_store.save(resolved_session_id)

    return AskResponse(
        saved=bool(api_result.get("saved", False)),
        answer=answer,
        session_id=resolved_session_id,
        api_health=a_health,
        tts_ok=tts_ok,
        tts_queued=tts_queued,
        tts_path=tts_path,
        interaction_id=api_result.get("interaction_id"),
        session_created=api_result.get("session_created"),
        messages_saved=api_result.get("messages_saved"),
    )


@app.post("/speak", response_model=SpeakResponse)
def speak(payload: SpeakPayload, background_tasks: BackgroundTasks = None) -> SpeakResponse:
    session_id = _resolve_session_id(payload.session_id)
    session_store.save(session_id)

    tts_path: Optional[str] = None
    tts_ok = False
    message_saved = False
    tts_queued = False

    if payload.save_message:
        try:
            api_client.save_session_message(
                session_id=session_id,
                role="assistant",
                content=payload.text,
                meta={"source": "voice_agent_speak", "kind": "wake_greeting"},
                session_kind="voice",
            )
            message_saved = True
        except Exception as exc:
            logger.warning("[speak] session_message save failed: %s", exc)

    try:
        if background_tasks is not None:
            background_tasks.add_task(synthesize_tts, payload.text, payload.voice_name, "speak")
            tts_ok = True
            tts_queued = True
        else:
            tts_path = synthesize_tts(payload.text, voice_name=payload.voice_name, prefix="speak")
            tts_ok = tts_path is not None
    except Exception as exc:
        logger.error("[speak] TTS synthesis failed: %s", exc)

    return SpeakResponse(
        saved=True,
        tts_ok=tts_ok,
        tts_queued=tts_queued,
        tts_path=tts_path,
        session_id=session_id,
        message_saved=message_saved,
    )


def main() -> None:
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=VOICE_AGENT_PORT, reload=False)


if __name__ == "__main__":
    main()
