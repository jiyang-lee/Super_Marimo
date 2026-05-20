from machine import Pin, ADC
import time

WATER_POWER_GPIO = 12
WATER_ADC = ADC(0)
STABILIZE = 0.3

power = Pin(WATER_POWER_GPIO, Pin.OUT)
values = []

print("Water calibration started (10 min, 10s interval)...")

for i in range(60):
    power.init(Pin.OUT)
    power.on()
    time.sleep(STABILIZE)
    raw = WATER_ADC.read()
    power.off()
    power.init(Pin.IN)
    values.append(raw)
    print("Sample", i + 1, ":", raw)
    if i < 59:
        time.sleep(10 - STABILIZE)

avg = sum(values) // len(values)
print("Average raw:", avg)

with open("water_calib.txt", "w") as f:
    f.write(str(avg) + "\n")

print("Calibration saved to water_calib.txt")
