# Voice Server

Voice Server는 **음성 처리 전용 서버**입니다.

## 역할
- RP2040 또는 오디오 입력 장치에서 들어온 음성 신호를 텍스트로 변환 (STT)
- LLM 응답 텍스트를 음성으로 변환 (TTS)

## 주요 API
- `GET /health`
- `POST /stt` (multipart 오디오 업로드)
- `POST /tts` (JSON text → wav 파일)

## 엔진
- STT: faster-whisper (CUDA/CPU fallback)
- TTS: supertonic-3
