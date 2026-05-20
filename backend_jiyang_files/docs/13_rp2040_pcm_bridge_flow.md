# RP2040 Nano PCM 스트림 + Bridge 감지 흐름

이 구성은 가장 단순한 형태의 음성 파이프라인입니다.

## 역할 분리

- RP2040 Nano
  - 전원 인가 후 PDM 마이크를 바로 시작한다.
  - 16kHz, 16-bit mono PCM을 시리얼로 계속 보낸다.
  - 말 감지, STT, LLM, TTS는 하지 않는다.

- Windows Bridge
  - 시리얼 PCM을 받아 VAD로 말 구간을 감지한다.
  - 감지된 세그먼트를 `voice-server /stt`로 보낸다.
  - 이어서 `api-server /voice/ask`를 호출하고, TTS를 재생한다.

## 업로드

1. RP2040 Nano를 COM4에 연결한다.
2. Arduino IDE에서 [`arduino/NanoPdmSerial.ino`](/C:/Projects/_active/Super_Marimo/arduino/NanoPdmSerial.ino)를 업로드한다.
3. 업로드 후 시리얼 모니터를 열지 않아도 동작해야 한다.

## 실행 순서

1. Docker 스택을 올린다.
   ```powershell
   cd C:\Projects\_active\Super_Marimo
   docker compose -f docker-compose.yml -f docker-compose.gpu.yml up -d --build db-server api-server llm-server voice-server voice-agent
   ```
2. Windows Bridge를 실행한다.
   ```powershell
   cd C:\Projects\_active\Super_Marimo
   pip install -r requirements-bridge.txt
   python -m bridge.main --port COM4
   ```
3. 말을 하면 Bridge가 감지하고 서버 흐름을 이어간다.

## 기대 동작

- 전원만 넣으면 RP2040가 계속 마이크 PCM을 보낸다.
- Bridge가 무음과 발화를 구분한다.
- 발화가 감지되면 STT → LLM → TTS 순서로 처리된다.

## 확인 포인트

- RP2040 쪽에서 `while (!Serial)`처럼 연결 대기를 하면 안 된다.
- Bridge가 `bridge/captures`에 남기는 디버그 WAV는 25개만 유지된다.
- TTS WAV는 재생 후 삭제된다.
