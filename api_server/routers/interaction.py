import json
from typing import Any

from fastapi import APIRouter, HTTPException
from fastapi.encoders import jsonable_encoder
from fastapi.responses import Response

from schemas import AskPayload, VoiceAskPayload
from services.interaction_service import handle_interaction

router = APIRouter()


def _utf8_json_response(payload: dict[str, Any]) -> Response:
    encoded = jsonable_encoder(payload)
    return Response(content=json.dumps(encoded, ensure_ascii=True), media_type="application/json")


@router.post("/ask")
async def ask(payload: AskPayload) -> Response:
    result = await handle_interaction(
        session_id=payload.session_id,
        text=payload.question.strip(),
        sensor=payload.sensor,
        use_sensor_context=payload.use_sensor_context,
        source="ask",
        persona_memo=payload.persona_memo,
        system_memo=payload.system_memo,
        is_test=payload.is_test or False,
    )
    return _utf8_json_response(result)


@router.post("/voice/ask")
async def voice_ask(payload: VoiceAskPayload) -> Response:
    text = payload.text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="text is required")

    result = await handle_interaction(
        session_id=payload.session_id,
        text=text,
        sensor=payload.sensor,
        use_sensor_context=payload.use_sensor_context,
        source="voice",
        persona_memo=payload.persona_memo,
        system_memo=payload.system_memo,
    )
    return _utf8_json_response(result)
