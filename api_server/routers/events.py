from typing import Any

from fastapi import APIRouter

from schemas import ManualTestEventPayload, WakewordEventPayload
from services.device_event_service import save_device_event

router = APIRouter()


@router.post("/events/wakeword")
def wakeword_event(payload: WakewordEventPayload) -> dict[str, Any]:
    return save_device_event(payload.model_dump())


@router.post("/events/manual-test")
def manual_test_event(payload: ManualTestEventPayload) -> dict[str, Any]:
    return save_device_event(payload.model_dump())
