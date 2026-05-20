# Wemos 센서 업로드 및 `/sensor` 대시보드 가이드

이 문서는 `arduino/wemos`의 MicroPython 펌웨어를 업로드하고, Wemos가 3초 주기로 센서를 읽어서 API 서버에 저장하는 흐름을 확인하는 방법을 정리한다.

## 1. 역할 분리

- `Nano`
  - 기존 음성/마이크 쪽 장치다.
  - 이번 작업 범위에서는 수정하지 않는다.
- `Wemos`
  - 센서 수집기다.
  - 3초마다 센서를 읽고 `realtime` / `hourly`를 각각 서버로 보낸다.
  - `water_raw`와 `light_raw`는 10분 간격으로 저장된다.

## 2. 펌웨어 위치

- `arduino/wemos/main.py`
- 업로드 보조 스크립트: `arduino/wemos/deploy.py`
- 설정 파일: `arduino/wemos/.env`

## 3. 필요한 것

- MicroPython이 올라간 ESP8266 보드
- `mpremote`
- Wemos D1 mini 계열 보드
- Wi-Fi 정보
- API 서버 주소

선택 사항:

- DHT 센서
  - 있으면 온습도를 읽는다.
  - 없어도 나머지 센서는 동작하도록 구성했다.

## 4. 업로드 명령

아래 명령은 Wemos 펌웨어를 업로드한다.

```powershell
cd C:\Projects\_active\Super_Marimo\arduino\wemos
python deploy.py --port COM3
```

`.env`를 먼저 채워두면 위 명령만으로 충분하다.

필요하면 CLI로 값을 덮어쓸 수 있다.

```powershell
python deploy.py --port COM3 --ssid "WIFI_SSID" --password "WIFI_PASSWORD" --api-base-url "http://192.168.219.43:8000"
```

## 5. 펌웨어가 보내는 데이터

Wemos는 3초마다 센서를 읽는다.

- `POST /sensor/realtime-ingest`
  - `light`
  - `distance`
- `POST /sensor/hourly-ingest`
  - `temperature`
  - `humidity`
  - `water_level`
  - `water_raw`
  - `light_raw`

`water_level`은 수위 ADC raw 값을 퍼센트로 환산한 값이다.

## 6. 확인 순서

1. `api-server`, `llm-server`, `voice-server`, `voice-agent`가 올라와 있는지 확인한다.
2. Wemos를 업로드한다.
3. 시리얼 로그에서 `T`, `H`, `Lx`, `W%`, `D`가 3초마다 갱신되는지 확인한다.
4. `water_raw`와 `light_raw`가 10분마다 `hourly-ingest`로 전송되는지 확인한다.
5. `frontend/sensor-dashboard.html`을 열어서 상단 카드가 최신 센서값으로 바뀌는지 본다.
6. 아래쪽 `realtime history`, `hourly history` 테이블에 row가 계속 쌓이는지 본다.
7. `최근 센서 이벤트`와 `최근 세션`에서 후속 흐름이 같이 살아 있는지 본다.

## 7. 대시보드

센서 전용 점검 화면은 아래 파일이다.

- `frontend/sensor-dashboard.html`

이 페이지에서 볼 것:

- 상단 카드
  - realtime 최신값
  - hourly 최신값
  - merged snapshot
  - 마지막 동기화 시각
- 하단 테이블
  - realtime history
  - hourly history
  - 이벤트 로그
  - 세션 로그

## 8. 실패할 때 보는 포인트

- 업로드가 실패한다
  - `mpremote`가 설치되어 있는지 확인한다.
  - COM 포트가 맞는지 확인한다.
  - 다른 시리얼 모니터가 포트를 잡고 있지 않은지 확인한다.
- Wi-Fi 연결이 안 된다
  - SSID / 비밀번호를 다시 확인한다.
  - 시리얼 로그에서 `Wi-Fi connection failed`가 나오는지 본다.
- API 저장이 안 된다
  - `API_BASE_URL`이 실제 API 서버 주소인지 확인한다.
  - `http://localhost:8000/health`가 먼저 살아 있는지 확인한다.
- 대시보드에 값이 안 바뀐다
  - `frontend/sensor-dashboard.html`의 API Base URL이 맞는지 확인한다.
  - Wemos에서 실제로 POST가 성공했는지 시리얼 로그를 본다.

## 9. 한 줄 요약

Wemos를 3초 tick 센서 수집기로 올리고, `frontend/sensor-dashboard.html`에서 저장된 값과 DB 누적 상태를 같이 확인하면 된다.
