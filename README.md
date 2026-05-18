# Super_Marimo

로컬 실험용 통합 저장소입니다. 현재 구조는 `voice-agent -> api-server -> db-server` 흐름의 백엔드와 `frontend/` 웹 UI를 함께 포함합니다.

## 구성
- `db-server`: PostgreSQL
- `api-server`: 세션 / 메시지 / 상호작용 저장
- `llm-server`: 응답 생성
- `voice-server`: STT / TTS
- `voice-agent`: 호출어 이후 대화 오케스트레이션
- `frontend`: 수동 테스트용 콘솔 UI

## 실행
백엔드 전체를 올릴 때:

```powershell
cd C:\Projects\_active\Super_Marimo
docker compose up -d --build db-server api-server llm-server voice-server voice-agent
```

현재 compose 기본값은 빠른 로컬 부트스트랩을 위한 `MOCK_MODE=true`입니다. 실제 모델로 바꿔 돌릴 때만 `docker-compose.yml`의 mock 값을 끄면 됩니다.

프런트엔드가 필요하면 별도로:

```powershell
cd C:\Projects\_active\Super_Marimo\frontend
npm install
npm run dev
```

## 포트
- API Server: `http://localhost:8000`
- LLM Server: `http://localhost:8001`
- Voice Server: `http://localhost:8002`
- Voice Agent: `http://localhost:8003`
- Frontend: `http://localhost:5173`
- PostgreSQL: `localhost:5432`

## 주요 API
### voice-server
- `GET /health`
- `POST /stt?model=fast`
- `POST /tts`

### llm-server
- `GET /health`
- `POST /generate`

### voice-agent
- `GET /health`
- `POST /ask`

### api-server
- `GET /health`
- `POST /ask`
- `POST /voice/ask`
- `POST /sensor/realtime-ingest`
- `POST /sensor/hourly-ingest`
- `GET /sessions`

## 동작 순서
1. `voice-agent`가 질문을 받습니다.
2. `voice-agent`가 `api-server /voice/ask`를 호출합니다.
3. `api-server`가 `llm-server`에 질문을 보내고 결과를 DB에 저장합니다.
4. `voice-agent`는 필요하면 `voice-server /tts`로 음성을 만듭니다.
5. `db-server`에는 `session`, `session_message`, `interaction_log`가 남습니다.

## 메모
- 호출어 감지는 `arduino/serial_voice_proto.py`의 루프에서 처리합니다.
- `voice-agent`는 그 뒤의 오케스트레이션 계층입니다.

## 규칙과 문서
- 프로젝트 규칙: `docs/01_프로젝트_규칙.md`
- GitHub 운영 규칙: `docs/03_GitHub_운영_규칙.md`
- 스킬 입력 가이드: `docs/02_스킬_가이드.md`
- 반복 작업 스킬: `skills/`

## 프론트엔드 작업 노트
- 현재 웹 UI 작업은 `frontend/jeong` 브랜치 기준으로 진행 중입니다.
- 참고 이미지: `ref/image.png`, `ref/marimo_character_transparent.png`
