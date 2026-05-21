from typing import Any, Literal, Optional

from fastapi import APIRouter, HTTPException

from schemas import DeviceEventPayload, ManualTestEventPayload, WakewordEventPayload
from services.device_event_service import (
    get_event,
    list_events,
    mark_event_played,
    normalize_event_type,
    save_device_event,
    update_event_status,
    ALLOWED_EVENT_STATUSES,
)

router = APIRouter()


@router.get("/events")
def device_event_list(
    event_type: Optional[str] = None,
    event_types: Optional[list[str]] = None,
    device_id: Optional[str] = None,
    status: Optional[str] = None,
    played: Optional[bool] = None,
    limit: int = 50,
    offset: int = 0,
    order: Literal["asc", "desc"] = "desc",
) -> dict[str, Any]:
    return list_events(
        event_type=event_type,
        event_types=event_types,
        device_id=device_id,
        status=status,
        played=played,
        limit=limit,
        offset=offset,
        order=order,
    )


@router.get("/events/{event_id}")
def device_event_detail(event_id: int) -> dict[str, Any]:
    return get_event(event_id)


@router.post("/events/{event_id}/played")
def device_event_mark_played(event_id: int) -> dict[str, Any]:
    return mark_event_played(event_id)


@router.put("/events/{event_id}/status")
def device_event_update_status(event_id: int, payload: dict[str, Any]) -> dict[str, Any]:
    status = str(payload.get("status") or "").strip()
    if status not in ALLOWED_EVENT_STATUSES:
        raise HTTPException(status_code=400, detail=f"status must be one of {sorted(ALLOWED_EVENT_STATUSES)}")
    return update_event_status(event_id, status)


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
