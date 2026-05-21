from __future__ import annotations

from typing import Any, Optional

from schemas import HourlySensorPayload, RealtimeSensorPayload, SensorPayload
from utils import now_kst


TEMPERATURE_HIGH_THRESHOLD_C = 30.0
TEMPERATURE_LOW_THRESHOLD_C = 20.0
WATER_LOW_THRESHOLD = 70.0
HUMIDITY_HIGH_THRESHOLD = 60.0
HUMIDITY_LOW_THRESHOLD = 30.0
LIGHT_DARK_THRESHOLD_LUX = 500.0
DAYLIGHT_START_HOUR = 13
DAYLIGHT_END_HOUR = 18


def _coerce_float(value: Any) -> Optional[float]:
    if value is None or isinstance(value, bool):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


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


def _apply_water_average(
    water_level: Optional[float],
    metrics: Optional[dict[str, Any]],
) -> Optional[float]:
    if metrics is None:
        return water_level
    water_avg = _coerce_float(metrics.get("water_level_recent_avg_2h"))
    if water_avg is not None:
        return water_avg
    return water_level


def _apply_light_average(
    light: Optional[float],
    metrics: Optional[dict[str, Any]],
) -> Optional[float]:
    if metrics is None:
        return light
    light_avg = _coerce_float(metrics.get("light_daytime_avg_13_18"))
    if light_avg is not None:
        return light_avg
    return light


def judge_realtime_state(
    payload: RealtimeSensorPayload | SensorPayload,
    metrics: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    from config import SENSOR_WARNING_DISTANCE_THRESHOLD_CM

    alerts: list[str] = []
    current_hour = int((metrics or {}).get("current_hour") or now_kst().hour)
    is_daylight_window = DAYLIGHT_START_HOUR <= current_hour < DAYLIGHT_END_HOUR

    temperature = _coerce_float(getattr(payload, "temperature", None))
    humidity = _coerce_float(getattr(payload, "humidity", None))
    water_level = _apply_water_average(_coerce_float(getattr(payload, "water_level", None)), metrics)
    light = _apply_light_average(_coerce_float(getattr(payload, "light", None)), metrics)
    distance = _coerce_float(getattr(payload, "distance", None))

    if light is not None and is_daylight_window and light <= LIGHT_DARK_THRESHOLD_LUX:
        alerts.append("조도가 낮음")
    if water_level is not None and water_level <= WATER_LOW_THRESHOLD:
        alerts.append("수위가 낮음")
    if temperature is not None:
        if temperature >= TEMPERATURE_HIGH_THRESHOLD_C:
            alerts.append("기온이 높음")
        elif temperature <= TEMPERATURE_LOW_THRESHOLD_C:
            alerts.append("기온이 낮음")
    if humidity is not None:
        if humidity >= HUMIDITY_HIGH_THRESHOLD:
            alerts.append("습도가 높음")
        elif humidity <= HUMIDITY_LOW_THRESHOLD:
            alerts.append("습도가 낮음")

    level = _level_from_alerts(alerts)
    return {
        "level": level,
        "rag": _rag_from_level(level),
        "alerts": alerts,
        "details": {
            "distance_threshold_cm": SENSOR_WARNING_DISTANCE_THRESHOLD_CM,
            "distance_cm": distance,
            "distance_role": "trigger_only",
            "water_level": _coerce_float(getattr(payload, "water_level", None)),
            "water_level_recent_avg_2h": water_level,
            "water_level_meaning": "higher is better",
            "temperature": temperature,
            "temperature_high_threshold_c": TEMPERATURE_HIGH_THRESHOLD_C,
            "humidity": humidity,
            "light": _coerce_float(getattr(payload, "light", None)),
            "light_daytime_avg_13_18": light,
            "light_daytime_window": f"{DAYLIGHT_START_HOUR:02d}:00~{DAYLIGHT_END_HOUR:02d}:00 KST",
            "light_daytime_meaning": "use daytime average as the reference",
        },
    }


def judge_hourly_state(
    payload: HourlySensorPayload,
    metrics: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    alerts: list[str] = []

    temperature = _coerce_float(payload.temperature)
    humidity = _coerce_float(payload.humidity)
    water_level = _apply_water_average(_coerce_float(payload.water_level), metrics)

    if temperature is not None:
        if temperature >= TEMPERATURE_HIGH_THRESHOLD_C:
            alerts.append("기온이 높음")
        elif temperature <= TEMPERATURE_LOW_THRESHOLD_C:
            alerts.append("기온이 낮음")

    if humidity is not None:
        if humidity >= HUMIDITY_HIGH_THRESHOLD:
            alerts.append("습도가 높음")
        elif humidity <= HUMIDITY_LOW_THRESHOLD:
            alerts.append("습도가 낮음")

    if water_level is not None and water_level <= WATER_LOW_THRESHOLD:
        alerts.append("수위가 낮음")

    level = _level_from_alerts(alerts)
    return {
        "level": level,
        "rag": _rag_from_level(level),
        "alerts": alerts,
        "details": {
            "water_level_band": "low" if (water_level is not None and water_level <= WATER_LOW_THRESHOLD) else ("high" if (water_level is not None and water_level >= 85) else "normal"),
            "water_level_recent_avg_2h": water_level,
            "water_level_meaning": "higher is better",
            "temperature_high_threshold_c": TEMPERATURE_HIGH_THRESHOLD_C,
        },
    }


def judge_sensor_state(
    sensor: SensorPayload,
    metrics: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    return judge_realtime_state(
        RealtimeSensorPayload(
            temperature=sensor.temperature,
            humidity=sensor.humidity,
            light=sensor.light,
            distance=sensor.distance,
            water_level=sensor.water_level,
        ),
        metrics=metrics
        or {
            "water_level_recent_avg_2h": getattr(sensor, "water_level_recent_avg_2h", None),
            "light_daytime_avg_13_18": getattr(sensor, "light_daytime_avg_13_18", None),
        },
    )
