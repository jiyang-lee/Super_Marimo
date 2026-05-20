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
docker compose -f docker-compose.yml -f docker-compose.gpu.yml up -d --build db-server api-server llm-server voice-server voice-agent
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

## 주소 설정

Bridge는 Windows Host에서 실행되므로 `127.0.0.1` 기준 주소를 사용합니다.
Docker 컨테이너 내부에서는 서비스 이름(`api-server:8000`)을 사용합니다.
자세한 주소 매트릭스는 `docs/network_address_matrix.md`를 참조하세요.

## 단계별 실행 가이드

### 1. Mock 모드로 전체 흐름 테스트
```powershell
cd C:\Projects\_active\Super_Marimo
docker compose -f docker-compose.yml -f docker-compose.mock.yml up -d --build
```

### 2. DB 정상 확인
```powershell
# 컨테이너 로그 확인
docker logs super-marimo-db-server
```

### 3. API 서버 healthcheck 확인
```powershell
Invoke-RestMethod -Uri http://localhost:8000/health
```

### 4. Voice Agent healthcheck 확인
```powershell
Invoke-RestMethod -Uri http://localhost:8003/health
```

### 5. 거리센서 이벤트 수동 테스트
```powershell
Invoke-RestMethod -Uri http://localhost:8000/sensor/realtime-ingest -Method POST -Body '{"distance": 5, "light": 300}' -ContentType "application/json"
```

### 6. Bridge 실행 (Windows Host)
```powershell
cd C:\Projects\_active\Super_Marimo
pip install -r requirements-bridge.txt
python -m bridge.main --port COM4
```

### 7. 실제 STT / TTS / LLM 모델 테스트 (GPU 모드)
```powershell
docker compose -f docker-compose.yml -f docker-compose.gpu.yml up -d --build
```

### 8. 모델 준비 상태 확인
```powershell
Invoke-RestMethod -Uri http://localhost:8001/ready
Invoke-RestMethod -Uri http://localhost:8002/ready
```

## Compose 파일별 목적

| 파일 | 목적 | 명령 |
|------|------|------|
| `docker-compose.yml` | 공통 베이스 | - |
| `docker-compose.mock.yml` | 모델 없이 전체 흐름 테스트 | `-f docker-compose.yml -f docker-compose.mock.yml up -d` |
| `docker-compose.cpu.yml` | CPU-only 모델 테스트 | `-f docker-compose.yml -f docker-compose.cpu.yml up -d` |
| `docker-compose.gpu.yml` | GPU 실행 모드 명시 | `-f docker-compose.yml -f docker-compose.gpu.yml up -d` |
| `docker-compose.dev.yml` | 소스코드 live reload | `-f docker-compose.yml -f docker-compose.dev.yml up -d` |

## 확인 URL

| 서비스 | Health | Ready |
|--------|--------|-------|
| API Server | `http://localhost:8000/health` | - |
| LLM Server | `http://localhost:8001/health` | `http://localhost:8001/ready` |
| Voice Server | `http://localhost:8002/health` | `http://localhost:8002/ready` |
| Voice Agent | `http://localhost:8003/health` | - |

## 메모

- Bridge는 Windows 전용입니다. COM 포트와 winsound(블루투스 스피커)에 직접 접근합니다.
- Voice Agent 컨테이너는 `./shared/audio/`를 Bridge와 공유합니다.
- 선제 인사 쿨다운 기본값은 60초입니다.
- `.env.mock`, `.env.cpu`, `.env.gpu`, `.env.local` 파일로 실행 모드와 로컬 주소를 분리했습니다.
