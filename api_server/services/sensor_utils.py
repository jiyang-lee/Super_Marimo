from typing import Any, Optional

from services.sensor_analytics import build_sensor_payload


def build_merged_payload(
    realtime_row: Optional[dict[str, Any]],
    hourly_row: Optional[dict[str, Any]],
    metrics: Optional[dict[str, Any]] = None,
) -> Optional[dict[str, Any]]:
    if realtime_row is None:
        if hourly_row is None:
            return None

    def _payload(row: Optional[dict[str, Any]]) -> dict[str, Any]:
        if row is None:
            return {}
        return dict(row.get("payload") or {})

    return build_sensor_payload(_payload(realtime_row), _payload(hourly_row), metrics=metrics)
