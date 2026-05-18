# Super_Marimo

RP2040 단일 테스트 환경에서 음성 이벤트 저장과 실제 TTS를 안정적으로 확인하는 로컬 스택입니다.

## 현재 구성
- `db-server`: PostgreSQL
- `api-server`: 세션, 이벤트, 센서 상태 저장
- `llm-server`: 응답 생성
- `voice-server`: STT / 실제 TTS
- `voice-agent`: `api-server`, `llm-server`, `voice-server`를 묶는 오케스트레이션
- `test/index.html`: `health`, `wakeword`, `manual-test`, `voice/ask`, `voice-server /tts`를 확인하는 최소 테스트 페이지

## 현재 목표
1. `wakeword` 저장
2. `manual-test` 저장
3. `voice/ask` 저장
4. `voice-server /tts` 실제 재생
5. DB에 `session`, `session_message`, `interaction_log`, `device_event_log`가 쌓이는지 확인

## 보류 항목
- 거리센서 기반 `sensor-warning`
- `proactive_greeting`
- 거리 쿨다운

## 실행
```powershell
cd C:\Projects\_active\Super_Marimo
docker compose up -d --build db-server api-server llm-server voice-server voice-agent
```

테스트 페이지:
```powershell
cd C:\Projects\_active\Super_Marimo
python -m http.server 5174 --directory test
```

브라우저:
```text
http://localhost:5174
```

## 주요 API
### voice-server
- `GET /health`
- `POST /stt`
- `POST /tts`

### voice-agent
- `GET /health`
- `POST /ask`

### api-server
- `GET /health`
- `POST /ask`
- `POST /voice/ask`
- `POST /events/wakeword`
- `POST /events/manual-test`
- `GET /sessions`

## 운영 메모
- 큰 변경이 생기면 `report/`에 보고서를 남깁니다.
- 테스트용 브랜치는 `backend/jiyang`을 사용합니다.
- 커밋 메시지는 한글로 작성합니다.
