from machine import Pin
import time

print("=== 백라이트 핀 테스트 ===")
print("1: GPIO14를 상단 핀에 연결하고 Enter")
print("2: GPIO14를 하단 핀에 연결하고 Enter")
print("3초마다 HIGH/LOW 바뀝니다")
print()

p = Pin(14, Pin.OUT)

for i in range(6):
    print("GPIO14 = HIGH")
    p.value(1)
    time.sleep(3)
    print("GPIO14 = LOW")
    p.value(0)
    time.sleep(3)

print("테스트 종료")
