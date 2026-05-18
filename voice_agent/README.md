# Voice Agent

`voice-agent`는 `api-server`, `llm-server`, `voice-server`를 묶는 오케스트레이션 계층입니다.

## 역할
- 상태 확인
- `api-server /voice/ask` 호출
- `voice-server /tts` 호출
- 필요하면 TTS 파일 재생

## 주요 API
- `GET /health`
- `POST /ask`

## 현재 기준
- 입력 장치가 아직 단순하므로, 현재는 텍스트 기반 `ask` 흐름을 우선합니다.
- 실제 음성 인식과 호출어 분리는 나중에 확장합니다.
