# Super_Marimo

Super_Marimo는 **디바이스 이벤트 중심**의 로컬 음성 대화 스택입니다. RP2040(Nano) 마이크와 Wemos 거리센서가 입력 장치이며, 프론트는 상태 모니터링과 수동 테스트용입니다.

## 동작 흐름

### A. 호출어 기반 대화
```
Nano 마이크
→ Bridge (호출어 감지 + VAD)
→ Voice Server (STT)
→ Voice Agent /ask
→ API Server /voice/ask
→ LLM Server
→ DB 저장
→ Voice Server (TTS)
→ ./shared/audio/에 wav 저장
→ Bridge audio_player (winsound) → 블루투스 스피커
```

### B. 거리센서 기반 선제 인사
```
Wemos 거리센서
→ API Server /sensor/realtime-ingest
→ 거리값 판단 + 쿨다운 확인
→ proactive_greeting 이벤트 생성
→ Voice Agent EventPoller가 /events 평
→ TTS 생성 → ./shared/audio/ 저장
→ Bridge audio_player → 블루투스 스피커
→ /events/{id}/played 로 마킹
```

### C. 프론트 수동 테스트
```
Frontend
→ Voice Agent /ask
→ LLM Server
→ DB 저장
→ Frontend 텍스트 응답 (+ 선택적 TTS 재생)
```

## 서비스 구성

| 서비스 | 역할 | 포트 |
|--------|------|------|
| db-server | PostgreSQL | 5432 |
| api-server | DB/LLM/정책 판단, 이벤트 저장 | 8000 |
| llm-server | 답변 생성 | 8001 |
| voice-server | STT / TTS | 8002 |
| voice-agent | 오케스트레이터 브레인, event poller | 8003 |
| bridge | Windows host 전용: 시리얼 + 스피커 | - |

## 실행

### Docker 서비스
```powershell
cd C:\Projects\_active\Super_Marimo
docker compose up -d --build db-server api-server llm-server voice-server voice-agent
```

### Bridge (Windows host)
```powershell
cd C:\Projects\_active\Super_Marimo
pip install -r requirements-bridge.txt
python -m bridge.main --port COM4
```

### 프론트
```powershell
cd C:\Projects\_active\Super_Marimo\frontend
npm install
npm run dev
```

프론트는 `http://localhost:5173`에서 열립니다.

## 메모

- Bridge는 Windows 전용입니다. COM 포트와 winsound(블루투스 스피커)에 직접 접근합니다.
- Voice Agent 컨테이너는 `./shared/audio/`를 Bridge와 공유합니다.
- 선제 인사 쿨다운 기본값은 60초입니다.
