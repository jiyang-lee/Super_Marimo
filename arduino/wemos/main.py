from machine import ADC, I2C, Pin
import gc
import network
import time


# ── .env parser ──────────────────────────────────────────────────────────────
def _parse_env(path=".env"):
    env = {}
    try:
        with open(path) as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" in line:
                    k, v = line.split("=", 1)
                    env[k.strip()] = v.strip()
    except Exception as e:
        print("env read error:", e)
    return env


_env = _parse_env()

try:
    import settings as runtime_settings
except Exception:
    runtime_settings = None


def _pick(name, default=""):
    if runtime_settings is not None and hasattr(runtime_settings, name):
        value = getattr(runtime_settings, name)
        if value not in (None, ""):
            return value
    return _env.get(name, default)


WIFI_SSID = _pick("WIFI_SSID", "U+NetE3CC")
WIFI_PASSWORD = _pick("WIFI_PASSWORD", "CHANGE_ME")
API_BASE_URL = _pick("API_BASE_URL", "http://192.168.219.43:8000")

# Pins
I2C_SCL_GPIO = 5
I2C_SDA_GPIO = 4
WATER_POWER_GPIO = 12
WATER_ADC = ADC(0)

# Sensor config
BH1750_ADDR = 0x23
BH1750_CONT_HIGH_RES = 0x10
WATER_STABILIZE_SECONDS = 0.3

# Runtime config
POLL_SECONDS = int(_pick("POLL_SECONDS", "10"))

# API endpoints
REALTIME_INGEST_URL = _pick("REALTIME_INGEST_URL", API_BASE_URL + "/sensor/realtime-ingest")


def ensure_wifi_connected():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    if wlan.isconnected():
        return True

    print("Connecting Wi-Fi...")
    wlan.connect(WIFI_SSID, WIFI_PASSWORD)
    for _ in range(20):
        if wlan.isconnected():
            print("Wi-Fi connected:", wlan.ifconfig()[0])
            return True
        time.sleep(1)
    print("Wi-Fi connection failed")
    return False


def init_i2c_and_bh1750():
    i2c = I2C(scl=Pin(I2C_SCL_GPIO), sda=Pin(I2C_SDA_GPIO), freq=100000)
    ok = False
    try:
        devices = i2c.scan()
        if BH1750_ADDR in devices:
            i2c.writeto(BH1750_ADDR, bytes([BH1750_CONT_HIGH_RES]))
            time.sleep_ms(180)
            ok = True
    except Exception as e:
        print("BH1750 init error:", e)
    return i2c, ok


def read_bh1750_raw(i2c, enabled):
    if not enabled:
        return None
    try:
        data = i2c.readfrom(BH1750_ADDR, 2)
        raw = (data[0] << 8) | data[1]
        return raw
    except Exception as e:
        print("BH1750 read error:", e)
        return None


def read_water_raw(power_pin):
    power_pin.init(Pin.OUT)
    power_pin.on()
    time.sleep(WATER_STABILIZE_SECONDS)
    raw = WATER_ADC.read()
    power_pin.off()
    power_pin.init(Pin.IN)
    return raw


def build_realtime_payload(light_raw, water_raw):
    payload = {
        "light": 0.0,
        "distance": 100.0,
    }
    if light_raw is not None:
        payload["light_raw"] = int(light_raw)
    if water_raw is not None:
        payload["water_raw"] = int(water_raw)
    return payload


def post_json(url, body, label):
    if not ensure_wifi_connected():
        print(label, "skipped (wifi disconnected)")
        return

    response = None
    try:
        gc.collect()
        import urequests

        response = urequests.post(url, json=body)
        print(label + ":", response.status_code)
        try:
            print(label + " resp:", response.json())
        except Exception:
            pass
    except Exception as e:
        print(label, "error:", e)
    finally:
        if response is not None:
            response.close()
        gc.collect()


def main():
    i2c, bh1750_enabled = init_i2c_and_bh1750()
    print("BH1750 ready" if bh1750_enabled else "BH1750 not found")
    ensure_wifi_connected()

    water_power = Pin(WATER_POWER_GPIO)

    while True:
        light_raw = read_bh1750_raw(i2c, bh1750_enabled)
        water_raw = read_water_raw(water_power)

        print(
            "Lraw:", light_raw,
            "Wraw:", water_raw,
        )

        payload = build_realtime_payload(light_raw, water_raw)
        post_json(REALTIME_INGEST_URL, payload, "Realtime ingest")

        gc.collect()
        time.sleep(POLL_SECONDS)


main()
