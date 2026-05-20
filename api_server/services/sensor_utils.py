from typing import Any, Optional

from schemas import SensorPayload
from services.sensor_store import extract_payload, get_latest_sensor_row


def build_merged_payload(
    realtime_row: Optional[dict[str, Any]],
    hourly_row: Optional[dict[str, Any]],
) -> Optional[dict[str, Any]]:
    from services.sensor_store import default_sensor_payload

    if realtime_row is None:
        return None

    merged_payload = default_sensor_payload().model_dump()
    realtime_payload = extract_payload(realtime_row)
    merged_payload["temperature"] = realtime_payload.get("temperature", merged_payload["temperature"])
    merged_payload["humidity"] = realtime_payload.get("humidity", merged_payload["humidity"])
    merged_payload["light"] = realtime_payload.get("light", merged_payload["light"])
    merged_payload["water_level"] = realtime_payload.get("water_level", merged_payload["water_level"])
    merged_payload["distance"] = realtime_payload.get("distance", merged_payload["distance"])
    return merged_payload
