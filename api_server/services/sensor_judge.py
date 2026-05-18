from typing import Any

from schemas import HourlySensorPayload, RealtimeSensorPayload, SensorPayload


def judge_realtime_state(payload: RealtimeSensorPayload) -> dict[str, Any]:
    from config import SENSOR_WARNING_DISTANCE_THRESHOLD_CM

    alerts: list[str] = []

    if payload.light <= 150:
        alerts.append("조도가 낮음")
    if payload.distance <= SENSOR_WARNING_DISTANCE_THRESHOLD_CM:
        alerts.append("물체가 가까움")
    level = "normal"
    if len(alerts) >= 2:
        level = "danger"
    elif alerts:
        level = "warning"
    return {"level": level, "alerts": alerts}


def judge_hourly_state(payload: HourlySensorPayload) -> dict[str, Any]:
    alerts: list[str] = []

    if payload.temperature >= 30:
        alerts.append("온도가 높음")
    elif payload.temperature <= 15:
        alerts.append("온도가 낮음")

    if payload.humidity >= 75:
        alerts.append("습도가 높음")
    elif payload.humidity <= 30:
        alerts.append("습도가 낮음")

    if payload.water_level <= 20:
        alerts.append("수위가 낮음")

    level = "normal"
    if len(alerts) >= 2:
        level = "danger"
    elif alerts:
        level = "warning"
    return {"level": level, "alerts": alerts}


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

    return {"level": level, "alerts": alerts}
