from machine import ADC, I2C, Pin, time_pulse_us
import dht
import gc
import network
import time


def _parse_env(path=".env"):
    env = {}
    try:
        with open(path) as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" in line:
                    key, value = line.split("=", 1)
                    env[key.strip()] = value.strip()
    except Exception as exc:
        print("env read error:", exc)
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


def _as_int(value, default):
    try:
        return int(value)
    except Exception:
        return default


def _as_hex_int(value, default):
    try:
        if isinstance(value, int):
            return value
        return int(str(value), 0)
    except Exception:
        return default


def _as_int_list(value, default):
    if isinstance(value, (list, tuple)):
        result = []
        for item in value:
            try:
                result.append(int(item))
            except Exception:
                pass
        return tuple(result) if result else default
    if value in (None, ""):
        return default
    result = []
    for part in str(value).replace("(", "").replace(")", "").split(","):
        part = part.strip()
        if not part:
            continue
        try:
            result.append(int(part, 0))
        except Exception:
            pass
    return tuple(result) if result else default


WIFI_SSID = _pick("WIFI_SSID", "U+NetE3CC")
WIFI_PASSWORD = _pick("WIFI_PASSWORD", "CHANGE_ME")
API_BASE_URL = _pick("API_BASE_URL", "http://192.168.219.43:8000")
REALTIME_INGEST_URL = _pick("REALTIME_INGEST_URL", API_BASE_URL + "/sensor/realtime-ingest")

I2C_SCL_GPIO = _as_int(_pick("I2C_SCL_GPIO", "5"), 5)
I2C_SDA_GPIO = _as_int(_pick("I2C_SDA_GPIO", "4"), 4)
HCSR04_TRIG_GPIO = _as_int(_pick("HCSR04_TRIG_GPIO", "14"), 14)
HCSR04_ECHO_GPIO = _as_int(_pick("HCSR04_ECHO_GPIO", "12"), 12)
DHT11_GPIO = _as_int(_pick("DHT11_GPIO", "13"), 13)
WATER_ADC = ADC(0)
WATER_POWER_GPIO = _as_int(_pick("WATER_POWER_GPIO", "16"), 16)

BH1750_ADDR = _as_hex_int(_pick("BH1750_ADDR", "0x23"), 0x23)
BH1750_CONT_HIGH_RES = _as_hex_int(_pick("BH1750_CONT_HIGH_RES", "0x10"), 0x10)

POLL_SECONDS = int(_pick("POLL_SECONDS", "1"))
WATER_STABILIZE_SECONDS = float(_pick("WATER_STABILIZE_SECONDS", "0.3"))
LCD_ADDR_CANDIDATES = _as_int_list(_pick("LCD_ADDR_CANDIDATES", (0x27, 0x3F)), (0x27, 0x3F))

LCD_CHR = 1
LCD_CMD = 0
LCD_BACKLIGHT = 0x08
LCD_ENABLE = 0x04
LCD_LINE_1 = 0x80
LCD_LINE_2 = 0xC0


def clamp(value, minimum, maximum):
    if value < minimum:
        return minimum
    if value > maximum:
        return maximum
    return value


def fmt_int(value):
    if value is None:
        return "-"
    return str(int(round(value)))


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
    except Exception as exc:
        print("BH1750 init error:", exc)
    return i2c, ok


def lcd_write_byte(i2c, addr, value):
    i2c.writeto(addr, bytes([value | LCD_BACKLIGHT]))


def lcd_toggle_enable(i2c, addr, value):
    time.sleep_us(500)
    lcd_write_byte(i2c, addr, value | LCD_ENABLE)
    time.sleep_us(500)
    lcd_write_byte(i2c, addr, value & ~LCD_ENABLE)
    time.sleep_us(500)


def lcd_send_byte(i2c, addr, value, mode):
    high = mode | (value & 0xF0)
    low = mode | ((value << 4) & 0xF0)
    lcd_write_byte(i2c, addr, high)
    lcd_toggle_enable(i2c, addr, high)
    lcd_write_byte(i2c, addr, low)
    lcd_toggle_enable(i2c, addr, low)


def lcd_command(i2c, addr, value):
    lcd_send_byte(i2c, addr, value, LCD_CMD)


def lcd_write_char(i2c, addr, value):
    lcd_send_byte(i2c, addr, value, LCD_CHR)


def init_lcd(i2c):
    try:
        devices = i2c.scan()
    except Exception as exc:
        print("LCD scan error:", exc)
        return None

    addr = None
    for candidate in LCD_ADDR_CANDIDATES:
        if candidate in devices:
            addr = candidate
            break
    if addr is None:
        return None

    time.sleep_ms(50)
    for value in (0x30, 0x30, 0x30, 0x20):
        lcd_write_byte(i2c, addr, value)
        lcd_toggle_enable(i2c, addr, value)
        time.sleep_ms(5)

    for cmd in (0x28, 0x0C, 0x06, 0x01):
        lcd_command(i2c, addr, cmd)
    time.sleep_ms(2)
    lcd_command(i2c, addr, 0x0C)
    time.sleep_ms(2)
    return addr


def lcd_print_line(i2c, addr, row, text):
    line = LCD_LINE_1 if row == 0 else LCD_LINE_2
    lcd_command(i2c, addr, line)
    text = text[:16]
    text = text + (" " * (16 - len(text)))
    for ch in text:
        lcd_write_char(i2c, addr, ord(ch))


def update_backlight(lux):
    global LCD_BACKLIGHT
    LCD_BACKLIGHT = 0x08


def update_lcd(i2c, lcd_addr, latest):
    if lcd_addr is None:
        return
    update_backlight(latest.get("light"))
    try:
        line1 = "T:{} H:{} L:{}".format(
            fmt_int(latest.get("temperature")),
            fmt_int(latest.get("humidity")),
            fmt_int(latest.get("light")),
        )
        line2 = "W:{} D:{}".format(
            fmt_int(latest.get("water_level")),
            fmt_int(latest.get("distance")),
        )
        lcd_print_line(i2c, lcd_addr, 0, line1)
        lcd_print_line(i2c, lcd_addr, 1, line2)
    except Exception as exc:
        print("LCD write error:", exc)


def read_dht11(sensor):
    try:
        sensor.measure()
        return sensor.temperature(), sensor.humidity()
    except Exception as exc:
        print("DHT read error:", exc)
        return None, None


def read_bh1750(i2c, enabled):
    if not enabled:
        return None, None
    try:
        data = i2c.readfrom(BH1750_ADDR, 2)
        raw = (data[0] << 8) | data[1]
        lux = raw / 1.2
        return raw, lux
    except Exception as exc:
        print("BH1750 read error:", exc)
        return None, None


def read_distance_cm(trigger, echo):
    try:
        echo.init(Pin.IN)
        trigger.off()
        time.sleep_us(2)
        trigger.on()
        time.sleep_us(10)
        trigger.off()
        duration = time_pulse_us(echo, 1, 30000)
        if duration < 0:
            return None
        return duration * 0.0343 / 2
    except Exception as exc:
        print("HC-SR04 read error:", exc)
        return None


def read_water_once(power_pin):
    try:
        power_pin.init(Pin.OUT)
        power_pin.on()
        time.sleep(WATER_STABILIZE_SECONDS)
        raw = WATER_ADC.read()
        power_pin.off()
        power_pin.init(Pin.IN)
        return raw, raw
    except Exception as exc:
        print("Water read error:", exc)
        return None, None


def build_realtime_payload(snapshot):
    payload = {}
    for key in ("temperature", "humidity", "light", "distance", "water_level"):
        value = snapshot.get(key)
        if value is not None:
            payload[key] = value
    return payload


def post_json(url, body):
    if not ensure_wifi_connected():
        print("realtime skipped (wifi disconnected)")
        return

    response = None
    try:
        gc.collect()
        import urequests

        response = urequests.post(url, json=body)
        print("realtime:", response.status_code)
        try:
            print("realtime resp:", response.json())
        except Exception:
            pass
    except Exception as exc:
        print("realtime error:", exc)
    finally:
        if response is not None:
            response.close()
        gc.collect()


def main():
    i2c, bh1750_enabled = init_i2c_and_bh1750()
    lcd_addr = init_lcd(i2c)
    print("BH1750 ready" if bh1750_enabled else "BH1750 not found")
    print("LCD ready" if lcd_addr is not None else "LCD not found")
    ensure_wifi_connected()

    dht11 = dht.DHT11(Pin(DHT11_GPIO))
    hcsr04_trig = Pin(HCSR04_TRIG_GPIO, Pin.OUT)
    hcsr04_echo = Pin(HCSR04_ECHO_GPIO, Pin.IN)
    water_power = Pin(WATER_POWER_GPIO, Pin.IN)

    latest = {
        "temperature": None,
        "humidity": None,
        "light": None,
        "distance": None,
        "water_level": None,
    }

    while True:
        temp_c, humidity = read_dht11(dht11)
        if temp_c is not None:
            latest["temperature"] = temp_c
        if humidity is not None:
            latest["humidity"] = humidity

        _, lux = read_bh1750(i2c, bh1750_enabled)
        if lux is not None:
            latest["light"] = float(lux)

        distance_cm = read_distance_cm(hcsr04_trig, hcsr04_echo)
        if distance_cm is not None:
            latest["distance"] = float(distance_cm)

        _, water_level = read_water_once(water_power)
        if water_level is not None:
            latest["water_level"] = int(water_level)

        print(
            "T:", latest["temperature"],
            "H:", latest["humidity"],
            "L:", latest["light"],
            "D:", latest["distance"],
            "W:", latest["water_level"],
        )

        update_lcd(i2c, lcd_addr, latest)
        post_json(REALTIME_INGEST_URL, build_realtime_payload(latest))

        gc.collect()
        time.sleep(POLL_SECONDS)


main()
