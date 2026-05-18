# API Server

API Server는 Super_Marimo의 중심 저장 및 정책 계층입니다.

## 역할
- 대화, 세션, 디바이스 이벤트, 센서 판정을 PostgreSQL에 기록
- `voice-agent`가 본은 질의를 `llm-server`와 연결
- STT / TTS 결과를 세션과 함께 저장
- **거리센서 선제 인사 정책** 판단 및 이벤트 생성
- 세션 조회 및 종료 처리

## 주요 API

### Health
- `GET /health`

### Interaction
- `POST /ask`
- `POST /voice/ask`

### Events
- `GET /events` (신규: 목록 조회)
- `GET /events/{event_id}` (신규: 단건 조회)
- `POST /events/{event_id}/played` (신규: played 마킹)
- `POST /events`
- `POST /events/wakeword`
- `POST /events/manual-test`

### Sensor
- `POST /sensor/status`
- `POST /sensor/ingest`
- `POST /sensor/realtime-ingest`
- `POST /sensor/hourly-ingest`
- `GET /sensor/latest`
- `GET /sensor/history`

### Sessions
- `GET /sessions`
- `GET /sessions/{session_id}`
- `POST /sessions/{session_id}/touch`
- `POST /sessions/{session_id}/end`

## 선제 인사 정책
`POST /sensor/realtime-ingest` 호출 시:
1. 거리 임계치(기본 10cm) 확인
2. `sensor_warning` 이벤트 저장
3. 쿨다운(기본 60초) 확인
4. `proactive_greeting` 이벤트 생성

`PROACTIVE_GREETING_USE_LLM=true` 설정 시 LLM으로 인사 문장을 생성합니다.
