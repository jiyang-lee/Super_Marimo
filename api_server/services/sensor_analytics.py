from __future__ import annotations

from collections import deque
from datetime import datetime, timedelta
from typing import Any, Optional

from config import DB_TIMEZONE
from schemas import HourlySensorPayload, RealtimeSensorPayload, SensorPayload
from utils import now_kst, normalize_response_payload


DAYLIGHT_START_HOUR = 13
DAYLIGHT_END_HOUR = 18
LIGHT_AVG_WINDOW_DAYS = 20
LIGHT_NORMALIZED_MIN_RAW = 2.0
LIGHT_NORMALIZED_MAX_RAW = 700.0
WATER_AVG_WINDOW_HOURS = 2


def _coerce_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    if isinstance(value, bool):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _payload_float(payload: dict[str, Any], key: str) -> Optional[float]:
    value = payload.get(key)
    if value is None:
        return None
    return _coerce_float(value)


def _avg(values: list[float]) -> Optional[float]:
    if not values:
        return None
    return sum(values) / len(values)


def _normalize_ratio_to_100(current: Any, reference: Any) -> Optional[int]:
    current_value = _coerce_float(current)
    reference_value = _coerce_float(reference)
    if current_value is None or reference_value is None or reference_value <= 0:
        return None
    normalized = int(round((current_value / reference_value) * 100))
    return max(0, min(100, normalized))


def _normalize_range_to_100(current: Any, minimum: float, maximum: float) -> Optional[int]:
    current_value = _coerce_float(current)
    if current_value is None or maximum <= minimum:
        return None
    normalized = round(((current_value - minimum) / (maximum - minimum)) * 100)
    return max(0, min(100, int(normalized)))


def _as_payload(value: Optional[dict[str, Any]]) -> dict[str, Any]:
    return dict(value or {})


def _sensor_payload_from_rows(realtime_payload: dict[str, Any] | None, hourly_payload: dict[str, Any] | None) -> dict[str, Any]:
    merged = SensorPayload(
        temperature=23.0,
        humidity=50.0,
        light=500.0,
        water_level=50.0,
        distance=100.0,
    ).model_dump()

    if hourly_payload:
        for key in ("temperature", "humidity", "water_level", "water_raw"):
            value = hourly_payload.get(key)
            if value is not None:
                merged[key] = value

    if realtime_payload:
        for key in ("temperature", "humidity", "light", "distance", "water_level", "light_raw", "water_raw"):
            value = realtime_payload.get(key)
            if value is not None:
                merged[key] = value

    return merged


def resolve_daylight_window(current: Optional[datetime] = None) -> tuple[datetime, datetime, str]:
    current_time = current or now_kst()
    local_now = current_time.astimezone(now_kst().tzinfo)
    if local_now.hour < DAYLIGHT_START_HOUR:
        base_day = (local_now - timedelta(days=1)).date()
    else:
        base_day = local_now.date()

    window_start = datetime(
        base_day.year,
        base_day.month,
        base_day.day,
        DAYLIGHT_START_HOUR,
        0,
        0,
        tzinfo=local_now.tzinfo,
    )
    window_end = datetime(
        base_day.year,
        base_day.month,
        base_day.day,
        DAYLIGHT_END_HOUR,
        0,
        0,
        tzinfo=local_now.tzinfo,
    )

    effective_end = min(local_now, window_end) if local_now.date() == base_day else window_end
    if effective_end < window_start:
        effective_end = window_end
    return window_start, effective_end, f"{DAYLIGHT_START_HOUR:02d}:00~{DAYLIGHT_END_HOUR:02d}:00 KST"


def compute_sensor_metrics(
    conn,
    *,
    current_payload: Optional[dict[str, Any]] = None,
    current_sensor_type: Optional[str] = None,
    current_time: Optional[datetime] = None,
) -> dict[str, Any]:
    current = current_time or now_kst()
    current_local = current.astimezone(now_kst().tzinfo)

    water_window_start = current - timedelta(hours=WATER_AVG_WINDOW_HOURS)
    daylight_window_start = current - timedelta(days=LIGHT_AVG_WINDOW_DAYS)
    daylight_end = current
    daylight_label = f"최근 {LIGHT_AVG_WINDOW_DAYS}일 {DAYLIGHT_START_HOUR:02d}:00~{DAYLIGHT_END_HOUR:02d}:00 KST 평균"
    is_daylight_hour = DAYLIGHT_START_HOUR <= current_local.hour < DAYLIGHT_END_HOUR

    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT created_at, payload, sensor_type
            FROM sensor_readings
            WHERE created_at >= %s
              AND created_at <= %s
            ORDER BY created_at ASC, reading_id ASC
            """,
            (water_window_start, current),
        )
        recent_rows = cur.fetchall() if hasattr(cur, "fetchall") else []
        recent_rows = recent_rows or []

        cur.execute(
            """
            SELECT created_at, payload, sensor_type
            FROM sensor_readings
            WHERE created_at >= %s
              AND created_at <= %s
            ORDER BY created_at ASC, reading_id ASC
            """,
            (daylight_window_start, daylight_end),
        )
        daylight_rows = cur.fetchall() if hasattr(cur, "fetchall") else []
        daylight_rows = daylight_rows or []

    water_values: list[float] = []
    for row in recent_rows:
        payload = _as_payload(row.get("payload"))
        water_value = _payload_float(payload, "water_level")
        if water_value is not None:
            water_values.append(water_value)

    light_values: list[float] = []
    for row in daylight_rows:
        payload = _as_payload(row.get("payload"))
        light_value = _payload_float(payload, "light")
        row_created_at = row.get("created_at")
        row_local = row_created_at.astimezone(now_kst().tzinfo) if row_created_at else None
        if light_value is not None and row_local is not None and DAYLIGHT_START_HOUR <= row_local.hour < DAYLIGHT_END_HOUR:
            light_values.append(light_value)

    if current_payload:
        current_water = _payload_float(current_payload, "water_level")
        if current_water is not None and (current_sensor_type != "hourly" or current_water not in water_values):
            water_values.append(current_water)

        current_light = _payload_float(current_payload, "light")
        if current_light is not None and is_daylight_hour:
            light_values.append(current_light)

    water_avg = _avg(water_values)
    light_avg = _avg(light_values)

    return {
        "current_time": current,
        "current_hour": current_local.hour,
        "water_window_start": water_window_start,
        "water_window_hours": WATER_AVG_WINDOW_HOURS,
        "water_level_recent_avg_2h": water_avg,
        "water_level_sample_count": len(water_values),
        "light_daytime_avg_13_18": light_avg,
        "light_daytime_sample_count": len(light_values),
        "light_daytime_window_start": daylight_window_start,
        "light_daytime_window_end": daylight_end,
        "light_daytime_window_label": daylight_label,
    }


def empty_sensor_metrics(current_time: Optional[datetime] = None) -> dict[str, Any]:
    current = current_time or now_kst()
    current_local = current.astimezone(now_kst().tzinfo)
    daylight_window_start = current - timedelta(days=LIGHT_AVG_WINDOW_DAYS)
    daylight_end = current
    daylight_label = f"최근 {LIGHT_AVG_WINDOW_DAYS}일 {DAYLIGHT_START_HOUR:02d}:00~{DAYLIGHT_END_HOUR:02d}:00 KST 평균"
    return {
        "current_time": current,
        "current_hour": current_local.hour,
        "water_window_start": current - timedelta(hours=WATER_AVG_WINDOW_HOURS),
        "water_window_hours": WATER_AVG_WINDOW_HOURS,
        "water_level_recent_avg_2h": None,
        "water_level_sample_count": 0,
        "light_daytime_avg_13_18": None,
        "light_daytime_sample_count": 0,
        "light_daytime_window_start": daylight_window_start,
        "light_daytime_window_end": daylight_end,
        "light_daytime_window_label": daylight_label,
    }


def safe_compute_sensor_metrics(
    conn,
    *,
    current_payload: Optional[dict[str, Any]] = None,
    current_sensor_type: Optional[str] = None,
    current_time: Optional[datetime] = None,
) -> dict[str, Any]:
    try:
        return compute_sensor_metrics(
            conn,
            current_payload=current_payload,
            current_sensor_type=current_sensor_type,
            current_time=current_time,
        )
    except Exception:
        return empty_sensor_metrics(current_time=current_time)


def build_sensor_semantics(metrics: dict[str, Any]) -> dict[str, Any]:
    return {
        "temperature_high_threshold_c": 30.0,
        "temperature_low_threshold_c": 20.0,
        "water_level_meaning": "water level is better when it is higher; use the recent 2 hour average",
        "water_level_recent_avg_2h": metrics.get("water_level_recent_avg_2h"),
        "water_level_sample_count": metrics.get("water_level_sample_count", 0),
        "light_meaning": f"light is summarized with the recent {LIGHT_AVG_WINDOW_DAYS} day KST 13:00-18:00 average and used as a daytime reference",
        "light_daytime_avg_13_18": metrics.get("light_daytime_avg_13_18"),
        "light_daytime_sample_count": metrics.get("light_daytime_sample_count", 0),
        "distance_meaning": "distance is only a proximity / position signal, not a danger signal",
        "distance_mode": "position_only",
    }


def build_sensor_summary(sensor: dict[str, Any], state: dict[str, Any], metrics: dict[str, Any]) -> str:
    temperature = _coerce_float(sensor.get("temperature"))
    humidity = _coerce_float(sensor.get("humidity"))
    water_level = _coerce_float(sensor.get("water_level"))
    light = _coerce_float(sensor.get("light"))
    distance = _coerce_float(sensor.get("distance"))
    water_avg = _coerce_float(metrics.get("water_level_recent_avg_2h"))
    light_avg = _coerce_float(metrics.get("light_daytime_avg_13_18"))
    parts: list[str] = []

    if temperature is not None:
        parts.append(f"기온 {temperature:.1f}°C")
    if humidity is not None:
        parts.append(f"습도 {humidity:.1f}%")
    if water_avg is not None:
        parts.append(f"수위 최근 2시간 평균 {water_avg:.1f}%")
    elif water_level is not None:
        parts.append(f"수위 {water_level:.1f}%")
    if light_avg is not None:
        parts.append(f"조도 {metrics.get('light_daytime_window_label', '13:00~18:00 KST')} 평균 {light_avg:.1f} lx")
    elif light is not None:
        parts.append(f"조도 {light:.1f} lx")
    if distance is not None:
        parts.append(f"거리 {distance:.1f} cm (위치 정보)")

    level = str(state.get("level") or "normal").strip() or "normal"
    prefix = f"현재 센서 상태는 {level}입니다."
    return f"{prefix} " + " / ".join(parts) if parts else prefix


def build_sensor_payload(
    realtime_payload: Optional[dict[str, Any]],
    hourly_payload: Optional[dict[str, Any]],
    metrics: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    merged = _sensor_payload_from_rows(realtime_payload, hourly_payload)
    if merged.get("water_level_raw") is None:
        merged["water_level_raw"] = merged.get("water_level")
    if merged.get("water_raw") is None:
        merged["water_raw"] = merged.get("water_level")
    if merged.get("light_raw") is None:
        merged["light_raw"] = merged.get("light")
    merged["light_normalized_0_100"] = _normalize_range_to_100(
        merged.get("light_raw") if merged.get("light_raw") is not None else merged.get("light"),
        LIGHT_NORMALIZED_MIN_RAW,
        LIGHT_NORMALIZED_MAX_RAW,
    )
    if metrics:
        water_avg = _coerce_float(metrics.get("water_level_recent_avg_2h"))
        light_avg = _coerce_float(metrics.get("light_daytime_avg_13_18"))
        merged["water_level_recent_avg_2h"] = water_avg
        merged["light_daytime_avg_13_18"] = light_avg
        merged["water_level_normalized_0_100"] = _normalize_ratio_to_100(merged.get("water_level"), water_avg)
        merged["water_level_sample_count"] = metrics.get("water_level_sample_count", 0)
        merged["light_daytime_sample_count"] = metrics.get("light_daytime_sample_count", 0)
        merged["light_daytime_window_label"] = metrics.get("light_daytime_window_label")
    return merged


def row_payload_to_sensor_payload(row_payload: dict[str, Any], metrics: Optional[dict[str, Any]] = None) -> SensorPayload:
    merged = build_sensor_payload(row_payload, None, metrics)
    return SensorPayload(**merged)


def rebuild_sensor_reading_states(conn) -> int:
    from services.sensor_judge import judge_hourly_state, judge_realtime_state

    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT reading_id, created_at, sensor_type, payload, state_level, state_alerts
            FROM sensor_readings
            ORDER BY created_at ASC, reading_id ASC
            """
        )
        rows = cur.fetchall() or []

    water_window: deque[tuple[datetime, float]] = deque()
    daylight_values_by_day: dict[datetime.date, list[float]] = {}
    updated_count = 0

    for row in rows:
        created_at = row["created_at"]
        local_created_at = created_at.astimezone(now_kst().tzinfo)
        payload = _as_payload(row.get("payload"))
        water_value = _payload_float(payload, "water_level")
        light_value = _payload_float(payload, "light")

        if water_value is not None:
            water_window.append((created_at, water_value))
        water_cutoff = created_at - timedelta(hours=WATER_AVG_WINDOW_HOURS)
        while water_window and water_window[0][0] < water_cutoff:
            water_window.popleft()

        if light_value is not None and DAYLIGHT_START_HOUR <= local_created_at.hour < DAYLIGHT_END_HOUR:
            daylight_values_by_day.setdefault(local_created_at.date(), []).append(light_value)

        daytime_day = local_created_at.date() if local_created_at.hour >= DAYLIGHT_START_HOUR else (local_created_at - timedelta(days=1)).date()
        water_avg = _avg([value for _, value in water_window])
        light_avg = _avg(daylight_values_by_day.get(daytime_day, []))
        metrics = {
            "current_time": created_at,
            "current_hour": local_created_at.hour,
            "water_level_recent_avg_2h": water_avg,
            "water_level_sample_count": len(water_window),
            "light_daytime_avg_13_18": light_avg,
            "light_daytime_sample_count": len(daylight_values_by_day.get(daytime_day, [])),
            "light_daytime_window_label": f"{DAYLIGHT_START_HOUR:02d}:00~{DAYLIGHT_END_HOUR:02d}:00 KST",
        }

        if row["sensor_type"] == "hourly":
            sensor_payload = HourlySensorPayload(
                temperature=_coerce_float(payload.get("temperature")) or 23.0,
                humidity=_coerce_float(payload.get("humidity")) or 50.0,
                water_level=_coerce_float(payload.get("water_level")) or 50.0,
            )
            state = judge_hourly_state(sensor_payload, metrics=metrics)
        else:
            sensor_payload = row_payload_to_sensor_payload(payload, metrics=metrics)
            state = judge_realtime_state(sensor_payload, metrics=metrics)

        state_level = str(state.get("level") or "normal")
        state_alerts = normalize_response_payload(state.get("alerts") or [])
        if state_level != row["state_level"] or state_alerts != normalize_response_payload(row["state_alerts"]):
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE sensor_readings
                    SET state_level = %s,
                        state_alerts = %s
                    WHERE reading_id = %s
                    """,
                    (state_level, normalize_response_payload(state_alerts), row["reading_id"]),
                )
                updated_count += 1

    conn.commit()
    return updated_count
