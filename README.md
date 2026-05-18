# Super_Marimo

Super_Marimo는 `voice-agent`를 게이트웨이로 두고, `api-server`가 대화/이벤트/세션을 저장하며, `voice-server`와 `llm-server`가 실제 STT/TTS/응답 생성을 맡는 로컬 음성 대화 스택입니다.

## 현재 구조

- `db-server`: PostgreSQL
- `api-server`: 대화 저장, 이벤트 저장, 센서 정책, 세션 종료
- `llm-server`: 답변 생성
- `voice-server`: STT / TTS
- `voice-agent`: `api-server`를 호출하는 경량 게이트웨이
- `frontend`: 모니터링용 UI
- `arduino/serial_voice_proto.py`: 호출어 감지와 음성 루프 실행

## 동작 흐름

1. 호출어 감지
2. 랜덤 인사 출력
3. 사용자 발화 수집
4. `api-server`로 질의 전달
5. `llm-server` 응답 생성
6. `voice-server` TTS 재생
7. 종료 멘트가 나오면 세션 종료 기록

## 주요 엔드포인트

### api-server

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

### voice-agent

- `GET /health`
- `POST /ask`

### voice-server

- `GET /health`
- `POST /stt`
- `POST /tts`

### llm-server

- `GET /health`
- `POST /generate`

## 실행

```powershell
cd C:\Projects\_active\Super_Marimo
docker compose up -d --build db-server api-server llm-server voice-server voice-agent
```

프론트 개발 서버:

```powershell
cd C:\Projects\_active\Super_Marimo\frontend
npm run dev
```

모니터링 UI는 브라우저에서 `http://localhost:5173` 로 열 수 있습니다.

## 메모

- 이번 정리에서는 프론트, 문서, voice-agent 단순화만 남겼습니다.
- 센서 하드웨어 실장 검증과 추가 기능은 범위 밖입니다.
