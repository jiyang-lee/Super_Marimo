import json
import threading
from typing import Any, Optional
from urllib import error as urlerror
from urllib import request as urlrequest


class EventLogger:
    def __init__(self, events_endpoint: str):
        self.events_endpoint = events_endpoint

    def log(
        self,
        event_type: str,
        *,
        session_id: Optional[str] = None,
        generated_text: str = "",
        played: bool = False,
        state_level: str = "chat",
        state_alerts: list[str] | None = None,
        sensor: dict[str, Any] | None = None,
        distance: float | None = None,
        meta: dict[str, Any] | None = None,
    ) -> None:
        payload = {
            "session_id": session_id,
            "device_id": "bridge",
            "trigger_source": "bridge",
            "event_type": event_type,
            "generated_text": generated_text,
            "played": played,
            "state_level": state_level,
            "state_alerts": state_alerts or [],
            "meta": meta or {},
        }
        if distance is not None:
            payload["distance"] = distance
        if sensor is not None:
            payload["sensor"] = sensor

        def _send() -> None:
            try:
                _post_json(self.events_endpoint, payload, timeout=15)
            except Exception as exc:
                print(f"[event] {event_type} log failed: {exc}")

        threading.Thread(target=_send, daemon=True).start()


def _post_json(url: str, payload: dict[str, Any], timeout: int) -> dict[str, Any]:
    data = json.dumps(payload).encode("utf-8")
    request = urlrequest.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urlrequest.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except urlerror.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {exc.code} from {url}: {detail}") from exc
