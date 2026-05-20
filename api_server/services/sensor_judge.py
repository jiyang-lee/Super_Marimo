from typing import Any

from schemas import HourlySensorPayload, RealtimeSensorPayload, SensorPayload
from utils import now_kst


LIGHT_DARK_THRESHOLD_LUX = 500.0
NIGHT_LIGHT_IGNORE_START_HOUR = 0
NIGHT_LIGHT_IGNORE_END_HOUR = 6


def _level_from_alerts(alerts: list[str]) -> str:
    if len(alerts) >= 2:
        return "danger"
    if alerts:
        return "warning"
    return "normal"


def _rag_from_level(level: str) -> str:
    if level == "danger":
        return "red"
    if level == "warning":
        return "amber"
    return "green"


def judge_realtime_state(payload: RealtimeSensorPayload) -> dict[str, Any]:
    from config import SENSOR_WARNING_DISTANCE_THRESHOLD_CM

    alerts: list[str] = []
    current_hour = now_kst().hour
    is_night_ignore = NIGHT_LIGHT_IGNORE_START_HOUR <= current_hour < NIGHT_LIGHT_IGNORE_END_HOUR

    if payload.light <= LIGHT_DARK_THRESHOLD_LUX and not is_night_ignore:
        alerts.append("조도가 낮음")
    if payload.distance <= SENSOR_WARNING_DISTANCE_THRESHOLD_CM:
        alerts.append("물체가 가까움")

    level = _level_from_alerts(alerts)
    return {
        "level": level,
        "rag": _rag_from_level(level),
        "alerts": alerts,
        "details": {
            "light": "night_ignored" if payload.light <= LIGHT_DARK_THRESHOLD_LUX and is_night_ignore else None,
            "distance_threshold_cm": SENSOR_WARNING_DISTANCE_THRESHOLD_CM,
        },
    }


def judge_hourly_state(payload: HourlySensorPayload) -> dict[str, Any]:
    alerts: list[str] = []

    if payload.temperature >= 27:
        alerts.append("온도가 높음")
    elif payload.temperature <= 20:
        alerts.append("온도가 낮음")

    if payload.humidity >= 60:
        alerts.append("습도가 높음")
    elif payload.humidity <= 30:
        alerts.append("습도가 낮음")

    if payload.water_level <= 70:
        alerts.append("수위가 낮음")

    level = _level_from_alerts(alerts)
    return {
        "level": level,
        "rag": _rag_from_level(level),
        "alerts": alerts,
        "details": {
            "water_level_band": "low" if payload.water_level <= 70 else ("normal" if payload.water_level < 85 else "high"),
            "water_raw": payload.water_raw,
        },
    }


def judge_sensor_state(sensor: SensorPayload) -> dict[str, Any]:
    realtime_state = judge_realtime_state(
        RealtimeSensorPayload(
            light=sensor.light,
            distance=sensor.distance,
        )
    )
    hourly_state = judge_hourly_state(
        HourlySensorPayload(
            temperature=sensor.temperature,
            humidity=sensor.humidity,
            water_level=sensor.water_level,
        )
    )

    alerts = realtime_state["alerts"] + hourly_state["alerts"]
    level = "normal"
    if len(alerts) >= 3:
        level = "danger"
    elif alerts:
        level = "warning"

    return {"level": level, "rag": _rag_from_level(level), "alerts": alerts}
