#!/usr/bin/env python3
"""Backfill hourly sensor rows for given hour numbers.

Usage: python scripts/backfill_hourly.py 20 21 22
If no hours provided, defaults to [20,21,22].
"""
from __future__ import annotations

import sys
from datetime import datetime, date, time, timedelta
from typing import List

import os
import sys

# Ensure api_server package is importable when running this script directly
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
API_SERVER_PATH = os.path.join(ROOT, "api_server")
if API_SERVER_PATH not in sys.path:
    sys.path.insert(0, API_SERVER_PATH)

from extensions.db import get_db_connection
from api_server.services.sensor_store import save_sensor_reading
from services.sensor_judge import judge_hourly_state
from services.sensor_analytics import compute_sensor_metrics


def most_recent_date_for_hour(target_hour: int, ref: datetime) -> date:
    # If ref.hour >= target_hour, use ref.date(), else use previous day
    if ref.hour >= target_hour:
        return ref.date()
    return (ref - timedelta(days=1)).date()


def build_hour_start(dt_date: date, hour: int) -> datetime:
    return datetime.combine(dt_date, time(hour=hour, minute=0, second=0))


def backfill_hours(hours: List[int]) -> None:
    now = datetime.now()
    with get_db_connection() as conn:
        for h in hours:
            target_date = most_recent_date_for_hour(h, now)
            hour_start = build_hour_start(target_date, h)
            hour_end = hour_start + timedelta(hours=1)

            with conn.cursor() as cur:
                # Try to compute AVG from realtime rows in that hour
                cur.execute(
                    """
                    SELECT
                        AVG((payload->>'temperature')::numeric) AS temperature,
                        AVG((payload->>'humidity')::numeric) AS humidity,
                        AVG((payload->>'light')::numeric) AS light,
                        AVG((payload->>'water_level')::numeric) AS water_level
                    FROM sensor_readings
                    WHERE sensor_type = 'realtime'
                      AND created_at >= %s
                      AND created_at < %s
                    """,
                    (hour_start, hour_end),
                )
                row = cur.fetchone()

                payload = {}
                if row and any(v is not None for v in row.values()):
                    if row["temperature"] is not None:
                        payload["temperature"] = float(row["temperature"])
                    if row["humidity"] is not None:
                        payload["humidity"] = float(row["humidity"])
                    if row["light"] is not None:
                        payload["light"] = float(row["light"])
                    if row["water_level"] is not None:
                        payload["water_level"] = float(row["water_level"])

                if not payload:
                    # No rows in that hour — pick one latest realtime row as fallback
                    cur.execute(
                        """
                        SELECT reading_id, created_at, payload
                        FROM sensor_readings
                        WHERE sensor_type = 'realtime'
                        ORDER BY created_at DESC
                        LIMIT 1
                        """
                    )
                    fallback = cur.fetchone()
                    if fallback and fallback.get("payload"):
                        p = fallback["payload"]
                        # copy available numeric fields
                        for key in ("temperature", "humidity", "light", "water_level"):
                            v = p.get(key)
                            if v is not None:
                                try:
                                    payload[key] = float(v)
                                except Exception:
                                    pass

                if not payload:
                    print(f"[backfill] no data available to build payload for hour {h}, skipping")
                    continue

                # Build state and save as hourly
                from schemas import HourlySensorPayload

                hp = HourlySensorPayload(**payload)
                metrics = compute_sensor_metrics(conn, current_payload=payload, current_sensor_type="hourly")
                state = judge_hourly_state(hp, metrics=metrics)

                # Insert with created_at set to hour_start via SQL in save_sensor_reading (it uses DB default),
                # so after insert we can update created_at to desired timestamp.
                res = save_sensor_reading(payload, "hourly", state)

                # Update the created_at of the inserted row to the hour_start
                inserted_id = res.get("reading_id")
                if inserted_id:
                    with conn.cursor() as cur2:
                        cur2.execute(
                            "UPDATE sensor_readings SET created_at = %s WHERE reading_id = %s",
                            (hour_start, inserted_id),
                        )
                    conn.commit()
                    print(f"[backfill] inserted hourly for {hour_start.isoformat()} (id={inserted_id}) payload={payload}")
                else:
                    print(f"[backfill] inserted hourly (no id returned) for {hour_start.isoformat()} payload={payload}")


def parse_args() -> List[int]:
    args = sys.argv[1:]
    if not args:
        return [20, 21, 22]
    hours: List[int] = []
    for a in args:
        try:
            h = int(a)
            if 0 <= h <= 23:
                hours.append(h)
        except Exception:
            pass
    return hours


if __name__ == "__main__":
    hrs = parse_args()
    if not hrs:
        print("No valid hours provided. Example: python scripts/backfill_hourly.py 20 21 22")
        sys.exit(1)
    backfill_hours(hrs)
