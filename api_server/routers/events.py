from typing import Any

from fastapi import APIRouter

from schemas import DeviceEventPayload, ManualTestEventPayload, WakewordEventPayload
from services.device_event_service import normalize_event_type, save_device_event

router = APIRouter()


@router.post("/events")
def device_event(payload: DeviceEventPayload) -> dict[str, Any]:
    return save_device_event(
        {
            **payload.model_dump(),
            "event_type": normalize_event_type(payload.event_type),
        }
    )


@router.post("/events/wakeword")
def wakeword_event(payload: WakewordEventPayload) -> dict[str, Any]:
    return save_device_event(payload.model_dump())


@router.post("/events/manual-test")
def manual_test_event(payload: ManualTestEventPayload) -> dict[str, Any]:
    return save_device_event(payload.model_dump())
