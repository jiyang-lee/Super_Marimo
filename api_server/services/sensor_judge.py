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

    water_level = getattr(payload, "water_level", None)
    temperature = getattr(payload, "temperature", None)
    humidity = getattr(payload, "humidity", None)

    if payload.light <= LIGHT_DARK_THRESHOLD_LUX and not is_night_ignore:
        alerts.append("어두움")
    if payload.distance <= SENSOR_WARNING_DISTANCE_THRESHOLD_CM:
        alerts.append("물체가 가까움")
    if water_level is not None and water_level <= 70:
        alerts.append("수위가 낮음")
    if temperature is not None:
        if temperature >= 27:
            alerts.append("기온이 높음")
        elif temperature <= 20:
            alerts.append("기온이 낮음")
    if humidity is not None:
        if humidity >= 60:
            alerts.append("습도가 높음")
        elif humidity <= 30:
            alerts.append("습도가 낮음")

    level = _level_from_alerts(alerts)
    return {
        "level": level,
        "rag": _rag_from_level(level),
        "alerts": alerts,
        "details": {
            "distance_threshold_cm": SENSOR_WARNING_DISTANCE_THRESHOLD_CM,
            "water_level": water_level,
            "temperature": temperature,
            "humidity": humidity,
            "night_light_ignored": bool(payload.light <= LIGHT_DARK_THRESHOLD_LUX and is_night_ignore),
        },
    }


def judge_hourly_state(payload: HourlySensorPayload) -> dict[str, Any]:
    alerts: list[str] = []

    if payload.temperature >= 27:
        alerts.append("기온이 높음")
    elif payload.temperature <= 20:
        alerts.append("기온이 낮음")

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
        },
    }


def judge_sensor_state(sensor: SensorPayload) -> dict[str, Any]:
    return judge_realtime_state(
        RealtimeSensorPayload(
            temperature=sensor.temperature,
            humidity=sensor.humidity,
            light=sensor.light,
            distance=sensor.distance,
            water_level=sensor.water_level,
        )
    )
