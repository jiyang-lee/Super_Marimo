# API Server

`api-server`는 세션, 대화, 이벤트, 센서 상태를 저장하는 백엔드입니다.

## 역할
- 세션 저장
- 대화 메시지 저장
- 호출어 이벤트 저장
- 수동 테스트 이벤트 저장
- 센서 상태 저장
- `llm-server`와의 연결

## 주요 API
- `GET /health`
- `POST /ask`
- `POST /voice/ask`
- `POST /events/wakeword`
- `POST /events/manual-test`
- `POST /sensor/status`
- `POST /sensor/realtime-ingest`
- `POST /sensor/hourly-ingest`
- `GET /sessions`
- `GET /sessions/{session_id}`

## 현재 기준
- `wakeword`와 `manual-test`는 바로 저장해서 확인할 수 있습니다.
- `voice/ask`는 텍스트 기반 음성 이벤트 저장과 LLM 연결용입니다.
- `sensor-warning`와 `proactive_greeting`은 다음 하드웨어가 붙을 때 다시 연결합니다.
- `interaction_log`와 `device_event_log`는 분리해서 저장합니다.
