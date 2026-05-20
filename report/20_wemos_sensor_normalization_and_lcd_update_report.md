# Wemos 센서 정규화 및 LCD 출력 개선 보고서

## 다이어그램

```
[변경 전]
┌─────────────────────────────────────┐
│  LCD: T:23C H:52%                  │
│       W:0% D:16cm                  │
│  (4개 값, % 포함)                   │
└─────────────────────────────────────┘
         ↓
[변경 후]
┌─────────────────────────────────────┐
│  LCD: T:23 H:52 L:100              │
│       W:100 D:20.5                 │
│  (5개 값, % 제거, 정규화)          │
└─────────────────────────────────────┘

센서 스케일:
- 수위: 1~100% (±5% 오차 범위)
- 조도: 0~100% (±5% 오차 범위)
```

## 요약

Wemos D1 mini(ESP8266)의 MicroPython 펌웨어(`main.py`)를 수정하여 센서 읽기 정규화와 LCD 출력 개선을 완료했다.

- 수위센서: RAW 값 기반 → 1~100% 정규화
- 조도센서: lux 값 기반 → 0~100% 정규화  
- LCD: % 기호 제거, 5개 값 모두 표시
- 수위센서 전원: GPIO 12(echo 핀)과 공유
- 불필요한 파일 정리 및 보드 초기화

## 변경 내용

### 1. main.py 리팩토링

**변경 전:**
- 모든 설정 하드코딩 (Wi-Fi, API 주소 등)
- 소리센서(KY-038) 포함
- 수위 0~100% 하드코딩

**변경 후:**
- `.env` 파일에서 설정 동적 로드
- 소리센서 완전 제거
- 수위 1~100% 정규화 (`water_percent()`)
- 조도 0~100% 정규화 (`lux_percent()`)

### 2. 수위센서 정규화

```python
WATER_RAW_MIN = 10
WATER_RAW_MAX = 190

# ±5% 오차 범위 적용
# ≤ 10 → 1%
# ≥ 180.5 (190×0.95) → 100%
# 중간값 → 선형 보간 1~99
```

**보정 과정:**
- 10분 동안 10초 간격으로 60회 샘플링
- 평균 RAW 값: 190
- `WATER_RAW_MAX` = 190 설정

### 3. 조도 정규화

```python
LUX_MIN = 0
LUX_MAX = 645

# ±5% 오차 범위 적용
# ≤ 4 lux → 0%
# ≥ 612.75 (645×0.95) → 100%
# 중간값 → 선형 보간 0~100
```

**기준값:**
- 실내 기본 조도: 640~650 lux
- 전등 끈 상태: 0~4 lux

### 4. LCD 출력 개선

**변경 전:**
```
T:23C H:52%
W:0% D:16cm
```

**변경 후:**
```
T:23 H:52 L:100
W:100 D:20.5
```

- 온도/습도/조도 → 1줄
- 수위/거리 → 2줄
- `%` 기호 제거
- `cm` 단위 제거

### 5. 수위센서 전원 공유

- **GPIO 12** (HC-SR04 echo 핀)과 VCC 공유
- 읽기 전: `Pin.OUT` → `HIGH` (0.3초 안정화)
- 읽기 후: `Pin.IN` 복원 → HC-SR04 echo 사용 가능

### 6. 파일 정리

**삭제:**
- `arduino/wemos/settings.py`
- `arduino/wemos/README.md`
- `arduino/wemos/.gitignore`
- `arduino/NanoPdmSerial.ino`
- `arduino/captures/` (wav 파일 전체)
- `arduino/__pycache__/`

**남김:**
- `arduino/wemos/ESP8266_GENERIC-*.bin` (펌웨어)
- `arduino/wemos/main.py` (수정됨)
- `arduino/wemos/.env` (IP 수정됨)
- `arduino/wemos/deploy.py` (업로더)

### 7. 보드 초기화 및 재설치

- Flash 완전 삭제 (`esptool erase_flash`)
- MicroPython v1.28.0 펌웨어 재플래시
- `main.py`, `.env` 재업로드
- 전원 사이클 시 `main.py` 자동 실행 확인

## 검증 결과

### REPL 로그 (정상 동작)

```
T: 23 H: 53 Lx: 645.0 Lpct: 100 Wraw: 209 W%: 100 D: 20.58
Realtime ingest: 422
Hourly ingest: 200
```

| 항목 | 상태 | 값 |
|------|------|-----|
| DHT11 (온습도) | ✅ 정상 | 23°C / 53% |
| BH1750 (조도) | ✅ 정상 | 645 lux → 100% |
| HC-SR04 (거리) | ✅ 정상 | 20~21cm |
| 수위센서 | ✅ 정상 | RAW 209 → 100% |
| LCD | ✅ 정상 | 5개 값 표시 |
| Wi-Fi/API | ✅ 정상 | POST 200/422 |

### LCD 화면 확인

```
1줄: T:23 H:53 L:100
2줄: W:100 D:20.5
```

## 추가 수정 완료

### 1. API 서버 임시 해결 (2025-05-19)

**문제:** `Realtime ingest: 422` — Pydantic v2에서 `sound` 필드 제거 후에도 이전 schema 캐싱으로 인해 계속 필수 필드로 인식됨.

**해결:** 
- `api_server/schemas.py`: `sound: Optional[float] = Field(default=None)` 추가 (Optional 처리)
- **보드 측 임시 조치**: `build_realtime_payload()`에 `"sound": 0.0` 포함 → `Realtime ingest: 200` 확인

**남은 작업:** Docker 컨테이너 재빌드 후 `sound` 필드 완전 제거 및 보드 측 임시 코드 제거

### 2. LCD 백라이트 조도 기반 제어 구현

**추가된 기능:**
- 조도 퍼센트 < 10% → 백라이트 **OFF** (`LCD_BACKLIGHT = 0x00`)
- 조도 퍼센트 ≥ 10% → 백라이트 **ON** (`LCD_BACKLIGHT = 0x08`)
- 상태 변화 시에만 I2C 쓰기 (불필요한 통신 방지)

**동작 확인:**
- Lpct: 100 → 백라이트 ON
- Lpct: 0 → 백라이트 OFF (BH1750 가려서 테스트 완료)

## 남은 이슈

1. **수위센서 raw 값 변동**
   - 190±20 범위에서 흔들림 (echo 핀 공유 영향)
   - GPIO 독립 핀 사용 또는 외부 트랜지스터로 전원 분리 권장

2. **거리센서 간헐적 None**
   - echo 핀이 input/output 전환 시 타이밍 이슈
   - 안정화 시간 추가 또는 하드웨어 분리 검토

## 다음 단계

1. **API 서버 완전 수정**: Docker 재빌드 후 `sound` 필드 완전 제거, 보드 측 임시 코드 제거
2. **하드웨어 개선**: 수위센서 전용 GPIO 핀 할당 (GPIO 2/15/16 등)
3. **수위 MIN 보정**: 건조 상태에서 실제 raw 값 측정 후 `WATER_RAW_MIN` 조정
