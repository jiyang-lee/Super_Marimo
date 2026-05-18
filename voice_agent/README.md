# Voice Agent

Voice Agent는 Super_Marimo의 **오케스트레이터 브레인**입니다.

## 역할
- HTTP Gateway (`/ask`, `/health`)
- **Event Poller**: `proactive_greeting`, `sensor_warning` 이벤트를 주기적으로 평
- TTS 생성 및 `./shared/audio/`에 wav 저장
- 세션 상태 관리

## 의존성
- API Server (이벤트 조회, /voice/ask)
- Voice Server (TTS)
- LLM Server (선제 인사 LLM 분기 시)

## 주요 API
- `GET /health`
- `POST /ask`

## 환경변수
- `API_SERVER_URL`
- `VOICE_SERVER_URL`
- `LLM_SERVER_URL`
- `SHARED_AUDIO_DIR` (기본: `/app/shared/audio`)
- `EVENT_POLLER_INTERVAL` (기본: 1.0초)

## Bridge와의 관계
Voice Agent는 "무엇을 말할지" 결정하고 TTS 파일을 생성합니다. 실제 스피커 출력은 Windows host의 Bridge가 담당합니다.
