# API Server

`api-server`는 Super_Marimo의 중심 저장 계층입니다. 대화, 세션, 디바이스 이벤트, 센서 판정을 받아 PostgreSQL에 기록합니다.

## 역할

- `voice-agent`가 보낸 질의를 `llm-server`와 연결
- STT / TTS 결과를 세션과 함께 저장
- 호출어, 발화, STT, LLM, TTS 이벤트 기록
- 센서 입력을 판정하고 `next_action` 반환
- 세션 조회 및 종료 처리

## 주요 API

- `GET /health`
- `POST /ask`
- `POST /voice/ask`
- `POST /events`
- `POST /events/wakeword`
- `POST /events/manual-test`
- `POST /sensor/status`
- `POST /sensor/ingest`
- `POST /sensor/realtime-ingest`
- `POST /sensor/hourly-ingest`
- `GET /sensor/latest`
- `GET /sensor/history`
- `GET /sessions`
- `GET /sessions/{session_id}`
- `POST /sessions/{session_id}/end`

## 현재 동작 포인트

- `wakeword`, `speech_started`, `speech_ended`, `stt_completed`, `llm_completed`, `tts_played` 이벤트가 저장됩니다.
- `sensor/realtime-ingest`는 거리 임계치와 쿨다운을 반영해 `sensor_warning` 또는 `proactive_greeting`을 반환할 수 있습니다.
- 종료 멘트가 들어오면 `POST /sessions/{session_id}/end`로 세션 종료 시각을 기록합니다.

## 실행

```powershell
cd C:\Projects\_active\Super_Marimo
uv run python -m api_server.main
```
