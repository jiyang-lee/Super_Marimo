#!/usr/bin/env python
# -*- coding: utf-8 -*-

import json
import sys
import time
from urllib import error as urlerror
from urllib import request as urlrequest

API_SERVER_URL = "http://127.0.0.1:8000"
INGEST_ENDPOINT = f"{API_SERVER_URL}/sensor/realtime-ingest"


def send_sensor_data(distance: float, light: float = 300.0) -> bool:
    payload = {
        "distance": distance,
        "light": light
    }
    data = json.dumps(payload).encode("utf-8")
    req = urlrequest.Request(
        INGEST_ENDPOINT,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    try:
        with urlrequest.urlopen(req, timeout=5) as response:
            res_data = json.loads(response.read().decode("utf-8"))
            print(f"\n[success] Sent distance={distance}cm | Response: {res_data}")
            return True
    except Exception as exc:
        print(f"\n[error] Failed to send sensor data: {exc}")
        print("[check] Is API server running? Run health check: http://localhost:8000/health")
        return False


def main():
    print("=" * 60)
    print("        Super Marimo - Interactive Sensor Simulator")
    print("=" * 60)
    print(f"Target API Server: {API_SERVER_URL}")
    print("This script simulates Wemos physical sensor distance inputs.")
    print("You can easily trigger 'proactive greeting' during a demo!")
    print("-" * 60)

    while True:
        print("\n[Menu]")
        print("1. [Trigger Greeting] Approach closely (5.0 cm)")
        print("2. [Reset] Move away (150.0 cm)")
        print("3. Enter custom distance")
        print("4. Exit")
        
        try:
            choice = input("\nSelect menu (1-4): ").strip()
        except KeyboardInterrupt:
            print("\nExiting simulator.")
            break

        if choice == "1":
            print("\n[Simulating] User approaching Marimo...")
            send_sensor_data(distance=5.0)
        elif choice == "2":
            print("\n[Simulating] User moving away...")
            send_sensor_data(distance=150.0)
        elif choice == "3":
            try:
                dist_str = input("Enter custom distance in cm (e.g. 25.5): ").strip()
                dist = float(dist_str)
                send_sensor_data(distance=dist)
            except ValueError:
                print("[invalid] Please enter a valid number.")
        elif choice == "4":
            print("\nExiting simulator. Have a great demo!")
            break
        else:
            print("[invalid] Invalid choice. Please choose 1, 2, 3, or 4.")
        
        time.sleep(0.5)


if __name__ == "__main__":
    main()
