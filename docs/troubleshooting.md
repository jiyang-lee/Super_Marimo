# 문제 해결 가이드

베타 테스트 중 자주 보는 실패 상황과 확인 위치를 빠르게 찾을 수 있도록 정리했다.

## 먼저 확인할 URL

```powershell
# API Server
Invoke-RestMethod http://localhost:8000/health

# LLM Server
Invoke-RestMethod http://localhost:8001/ready

# Voice Server
Invoke-RestMethod http://localhost:8002/ready

# Voice Agent
Invoke-RestMethod http://localhost:8003/health
```

## 실패 상황별 확인 위치

| 증상 | 확인 위치 | 바로 볼 명령 |
|---|---|---|
| DB 연결 실패 | `api-server` 로그 | `docker logs super-marimo-api-server` |
| LLM 응답 없음 | `llm-server` 로그 | `docker logs super-marimo-llm-server` |
| STT 결과 없음 | `voice-server` 로그 | `docker logs super-marimo-voice-server` |
| TTS 파일 생성 실패 | `voice-agent` 또는 `voice-server` 로그 | `docker logs super-marimo-voice-agent` |
| TTS 파일은 있는데 재생이 안 됨 | Windows Bridge `audio_player` 로그 | Bridge 터미널 출력 확인 |
| 센서 경고가 너무 자주 쌓임 | `api-server` sensor policy / `device_event_log` | DB에서 `sensor_warning` 중복 여부 확인 |
| 이벤트가 반복 재생됨 | `voice-agent` event poller / Bridge | `voice-agent`와 Bridge 로그를 함께 확인 |

## 이벤트 상태 확인

```powershell
# 아직 처리되지 않은 이벤트만 보기
Invoke-RestMethod "http://localhost:8000/events?status=pending&played=false&limit=10"

# 상태를 포함한 최근 이벤트 확인
Invoke-RestMethod "http://localhost:8000/events?limit=10"

# 특정 이벤트 상세
Invoke-RestMethod "http://localhost:8000/events/123"
```

## Bridge 디버깅

Bridge는 Windows에서 직접 실행하므로 터미널 출력을 실시간으로 봐야 한다.

```powershell
python -m bridge.main --port COM4 --debug-dir bridge\captures
```

- `--debug-dir`를 주면 PCM/WAV 캡처를 남길 수 있다.
- `[audio_player]` 로그에서 `playing`, `played`, `failed` 전이를 확인한다.

## 자주 보는 원인

- API 서버가 안 올라옴: DB 준비가 끝나지 않았거나 `DATABASE_URL`이 잘못됨.
- LLM/Voice가 `ready`를 못 넘음: 모델 다운로드나 GPU/CPU 모드 설정이 맞지 않음.
- Bridge가 소리를 못 냄: COM 포트, 블루투스 스피커, Windows 오디오 장치 확인 필요.
- 이벤트가 반복됨: `status` 전이와 `played` 반영 여부를 먼저 확인.
- `bridge/captures` keeps only the newest 25 `segment-*.wav` files by default; use `--debug-retain-count` to change the limit.
