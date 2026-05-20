from __future__ import annotations

import base64
import argparse
import os
import subprocess
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parent
MAIN_PATH = ROOT / "main.py"
SETTINGS_PATH = ROOT / "settings.py"
ENV_PATH = ROOT / ".env"
MPREMOTE_DEFAULT = Path.home() / ".local" / "bin" / "mpremote.exe"


def load_env_file(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists():
        return values

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip("'").strip('"')
    return values


def write_settings(env_values: dict[str, str]) -> None:
    def pick(name: str, default: str = "") -> str:
        return os.getenv(name) or env_values.get(name, default)

    api_base_url = pick("API_BASE_URL", "http://192.168.219.43:8000").rstrip("/")

    settings = "\n".join(
        [
            "# Auto-generated from .env by deploy.py",
            f'WIFI_SSID = {pick("WIFI_SSID")!r}',
            f'WIFI_PASSWORD = {pick("WIFI_PASSWORD")!r}',
            f'API_BASE_URL = {api_base_url!r}',
            f'REALTIME_INGEST_URL = {pick("REALTIME_INGEST_URL", api_base_url + "/sensor/realtime-ingest")!r}',
            f'DEVICE_ID = {pick("DEVICE_ID", "wemos_sensor_node")!r}',
            f'POLL_SECONDS = {int(float(pick("POLL_SECONDS", "1")))}',
            f'I2C_SCL_GPIO = {int(float(pick("I2C_SCL_GPIO", "5")))}',
            f'I2C_SDA_GPIO = {int(float(pick("I2C_SDA_GPIO", "4")))}',
            f'HCSR04_TRIG_GPIO = {int(float(pick("HCSR04_TRIG_GPIO", "14")))}',
            f'HCSR04_ECHO_GPIO = {int(float(pick("HCSR04_ECHO_GPIO", "12")))}',
            f'DHT11_GPIO = {int(float(pick("DHT11_GPIO", "13")))}',
            f'WATER_POWER_GPIO = {int(float(pick("WATER_POWER_GPIO", "16")))}',
            f'BH1750_ADDR = {int(pick("BH1750_ADDR", "0x23"), 0)}',
            f'BH1750_CONT_HIGH_RES = {int(pick("BH1750_CONT_HIGH_RES", "0x10"), 0)}',
            f'WATER_RAW_MIN = {int(float(pick("WATER_RAW_MIN", "10")))}',
            f'WATER_RAW_MAX = {int(float(pick("WATER_RAW_MAX", "190")))}',
            f'WATER_STABILIZE_SECONDS = {float(pick("WATER_STABILIZE_SECONDS", "0.3"))}',
            f'LCD_ADDR_CANDIDATES = {tuple(int(x, 0) for x in pick("LCD_ADDR_CANDIDATES", "0x27,0x3F").split(",") if x.strip())!r}',
            "",
        ]
    )
    SETTINGS_PATH.write_text(settings, encoding="utf-8")


def resolve_mpremote(cli_arg: str) -> str:
    candidate = Path(cli_arg)
    if candidate.exists():
        return str(candidate)
    if MPREMOTE_DEFAULT.exists():
        return str(MPREMOTE_DEFAULT)
    return cli_arg


def run(cmd: list[str]) -> None:
    print("+ " + " ".join(cmd))
    subprocess.run(cmd, check=True)


def interrupt_running_program(port: str) -> None:
    try:
        import serial
    except ImportError:
        return

    try:
        with serial.Serial(port, baudrate=115200, timeout=1, write_timeout=1) as ser:
            ser.reset_input_buffer()
            ser.reset_output_buffer()
            ser.write(b"\x03\x03\x03")
            ser.flush()
            time.sleep(0.6)
    except Exception as exc:
        print(f"[deploy] interrupt skipped: {exc}")


def read_until(ser, token: bytes, timeout: float = 5.0) -> bytes:
    deadline = time.time() + timeout
    buffer = bytearray()
    while time.time() < deadline:
        chunk = ser.read(ser.in_waiting or 1)
        if chunk:
            buffer.extend(chunk)
            if token in buffer:
                return bytes(buffer)
        else:
            time.sleep(0.05)
    raise TimeoutError(f"Timed out waiting for {token!r}")


def enter_raw_repl(ser) -> None:
    # Drain any pending output aggressively
    ser.reset_input_buffer()
    time.sleep(0.2)
    ser.read(ser.in_waiting or 0)

    # Send Ctrl+C repeatedly to break running main.py
    for _ in range(5):
        ser.write(b"\x03")
        ser.flush()
        time.sleep(0.1)

    time.sleep(0.3)
    ser.read(ser.in_waiting or 0)

    # Send Ctrl+A to enter raw REPL
    ser.write(b"\r\x01")
    ser.flush()
    read_until(ser, b"raw REPL", timeout=10.0)


def exec_raw_repl(ser, script: str) -> bytes:
    ser.write(script.encode("utf-8") + b"\x04")
    ser.flush()
    return read_until(ser, b"DEPLOY_OK", timeout=20.0)


def erase_existing_files(port: str) -> None:
    """Wemos의 main.py, settings.py를 raw REPL로 삭제"""
    try:
        import serial
    except ImportError:
        print("[deploy] pyserial not available, skipping erase")
        return

    try:
        with serial.Serial(port, baudrate=115200, timeout=2, write_timeout=2) as ser:
            ser.reset_input_buffer()
            ser.reset_output_buffer()
            for _ in range(5):
                ser.write(b"\x03")
                ser.flush()
                time.sleep(0.1)
            time.sleep(0.3)
            ser.read(ser.in_waiting or 0)
            ser.write(b"\r\x01")
            ser.flush()
            try:
                read_until(ser, b"raw REPL", timeout=5.0)
            except TimeoutError:
                print("[deploy] raw REPL not found, erase skipped")
                return
            script = (
                "import os\n"
                "for f in ('main.py', 'settings.py'):\n"
                "    try:\n"
                "        os.remove(f)\n"
                "    except OSError:\n"
                "        pass\n"
                "print('DEPLOY_OK')\n"
            )
            result = exec_raw_repl(ser, script)
            print("[deploy] erase result:", result.decode("utf-8", errors="replace").strip())
    except Exception as exc:
        print(f"[deploy] erase warning: {exc}")


def write_file_raw(port: str, remote_path: str, content: bytes) -> bytes:
    try:
        import serial
    except ImportError as exc:
        raise SystemExit("pyserial is required for the MicroPython deploy fallback") from exc

    with serial.Serial(port, baudrate=115200, timeout=1, write_timeout=1) as ser:
        ser.reset_input_buffer()
        ser.reset_output_buffer()
        ser.write(b"\x03\x03\x03")
        ser.flush()
        time.sleep(0.6)
        enter_raw_repl(ser)
        encoded = base64.b64encode(content).decode("ascii")
        script = "\n".join(
            [
                "import ubinascii",
                f"f = open({remote_path!r}, 'wb')",
                f"f.write(ubinascii.a2b_base64({encoded!r}))",
                "f.close()",
                "print('DEPLOY_OK')",
                "",
            ]
        )
        return exec_raw_repl(ser, script)


def main() -> int:
    parser = argparse.ArgumentParser(description="Deploy the Wemos MicroPython sensor firmware with mpremote.")
    parser.add_argument("--port", required=True, help="Serial port, e.g. COM3")
    parser.add_argument("--cli", default="mpremote", help="mpremote executable")
    parser.add_argument("--env-file", default=str(ENV_PATH), help="Optional .env file")
    parser.add_argument("--ssid", help="Wi-Fi SSID override")
    parser.add_argument("--password", help="Wi-Fi password override")
    parser.add_argument("--api-base-url", help="API base URL override, e.g. http://192.168.219.43:8000")
    args = parser.parse_args()

    mpremote = resolve_mpremote(args.cli)
    env_values = load_env_file(Path(args.env_file))
    if args.ssid:
        env_values["WIFI_SSID"] = args.ssid
    if args.password:
        env_values["WIFI_PASSWORD"] = args.password
    if args.api_base_url:
        env_values["API_BASE_URL"] = args.api_base_url
    write_settings(env_values)

    if not MAIN_PATH.exists():
        raise SystemExit(f"Missing firmware file: {MAIN_PATH}")

    # 1. Erase old files first
    erase_existing_files(args.port)

    # 2. Upload new files
    try:
      write_file_raw(args.port, "main.py", MAIN_PATH.read_bytes())
      write_file_raw(args.port, "settings.py", SETTINGS_PATH.read_bytes())
      return 0
    except Exception as exc:
        print(f"[deploy] raw serial upload failed: {exc}")

    # Fallback: try mpremote reset to break running main.py, then deploy
    print(f"[deploy] attempting mpremote reset on {args.port} ...")
    try:
        subprocess.run([mpremote, "connect", args.port, "reset"], check=False, timeout=5)
    except Exception as exc:
        print(f"[deploy] mpremote reset failed (expected if port drops): {exc}")

    # Wait for board to reboot and USB serial to reconnect
    print("[deploy] waiting 3s for board reboot ...")
    time.sleep(3.0)

    # Retry file copy after reset
    for attempt in range(1, 4):
        print(f"[deploy] mpremote fs cp attempt {attempt}/3 ...")
        try:
            run([mpremote, "connect", args.port, "fs", "cp", str(MAIN_PATH), ":main.py"])
            run([mpremote, "connect", args.port, "fs", "cp", str(SETTINGS_PATH), ":settings.py"])
            run([mpremote, "connect", args.port, "reset"])
            return 0
        except subprocess.CalledProcessError as exc:
            print(f"[deploy] attempt {attempt} failed: {exc}")
            if attempt < 3:
                print("[deploy] retrying after 2s ...")
                time.sleep(2.0)
            else:
                raise SystemExit("mpremote deploy failed after 3 attempts") from exc
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
