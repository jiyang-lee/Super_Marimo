#!/usr/bin/env python3
"""
30-minute monitoring script for light_raw and water_raw samples.
Run this and leave it running for 30 minutes.
It sends hourly-ingest every 10 minutes and logs DB counts.

Usage:
    python scripts/monitor_raw_samples.py
"""

import json
import time
from datetime import datetime, timezone
from urllib.request import Request, urlopen

API_URL = "http://localhost:8000/sensor/hourly-ingest"
DB_CHECK_URL = "http://localhost:8000/sensor/light-raw-samples?limit=144"
WATER_CHECK_URL = "http://localhost:8000/sensor/water-raw-samples?limit=144"
INTERVAL_SECONDS = 600  # 10 minutes
MONITOR_MINUTES = 30


def send_hourly(light_raw: int, water_raw: int) -> dict:
    payload = json.dumps({
        "temperature": 25.0,
        "humidity": 50.0,
        "water_level": 60.0,
        "water_raw": water_raw,
        "light_raw": light_raw,
    }).encode("utf-8")
    req = Request(API_URL, data=payload, headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urlopen(req, timeout=10) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception as exc:
        return {"error": str(exc)}


def check_db() -> dict:
    try:
        with urlopen(DB_CHECK_URL, timeout=10) as resp:
            light_data = json.loads(resp.read().decode("utf-8"))
        with urlopen(WATER_CHECK_URL, timeout=10) as resp:
            water_data = json.loads(resp.read().decode("utf-8"))
        return {
            "light_count": light_data.get("samples", []).__len__(),
            "water_count": water_data.get("samples", []).__len__(),
            "latest_light": light_data.get("samples", [])[-1:] if light_data.get("samples") else None,
            "latest_water": water_data.get("samples", [])[-1:] if water_data.get("samples") else None,
        }
    except Exception as exc:
        return {"error": str(exc)}


def main() -> None:
    start = time.time()
    iteration = 0
    print(f"[{now()}] Monitoring started for {MONITOR_MINUTES} minutes")
    print(f"[{now()}] Sending hourly-ingest every {INTERVAL_SECONDS}s")

    while (time.time() - start) < (MONITOR_MINUTES * 60):
        iteration += 1
        light_val = 400 + iteration
        water_val = 600 + iteration
        print(f"[{now()}] Sending light_raw={light_val}, water_raw={water_val}")
        result = send_hourly(light_val, water_val)
        lr = result.get("light_raw_sample", {})
        wr = result.get("water_raw_sample", {})
        print(f"[{now()}] light: saved={lr.get('saved')}, raw={lr.get('raw_value')}, skipped={lr.get('skipped')}")
        print(f"[{now()}] water: saved={wr.get('saved')}, raw={wr.get('raw_value')}")

        db = check_db()
        print(f"[{now()}] DB status: light={db.get('light_count')}, water={db.get('water_count')}")
        print("-" * 60)

        # Sleep until next interval
        elapsed = time.time() - start
        next_tick = ((elapsed // INTERVAL_SECONDS) + 1) * INTERVAL_SECONDS
        sleep_sec = next_tick - elapsed
        if sleep_sec > 0:
            time.sleep(sleep_sec)

    print(f"[{now()}] Monitoring complete!")
    db = check_db()
    print(f"[{now()}] Final DB status: light={db.get('light_count')}, water={db.get('water_count')}")


def now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


if __name__ == "__main__":
    main()
