# Voice Agent

`voice-agent`는 로컬 음성 대화의 오케스트레이션 계층입니다.

## 역할
- `api-server /voice/ask` 호출
- 세션 ID 보관
- `voice-server /tts` 요청
- `voice-server`, `llm-server`, `api-server` health 확인

## 현재 흐름
1. 질의를 받는다.
2. `api-server`로 보내 세션과 대화 로그를 저장한다.
3. 답변을 받아 필요하면 `voice-server`로 TTS를 만든다.
4. 호출어 루프는 `arduino/serial_voice_proto.py`가 담당한다.

## 실행
```powershell
cd C:\Projects\_active\Super_Marimo
docker compose up -d --build voice-agent
```
