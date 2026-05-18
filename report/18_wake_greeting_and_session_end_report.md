# 호출어 인사와 세션 종료 정리 보고서

```mermaid
flowchart LR
    WAKE[호출어 감지] --> GREET[랜덤 인사 재생]
    GREET --> LISTEN[대화 청취]
    LISTEN --> ASK[api-server /voice/ask]
    ASK --> ANSWER[응답 TTS]
    ANSWER --> LISTEN
    LISTEN --> EXIT{종료 멘트?}
    EXIT -- 예 --> END[POST /sessions/{session_id}/end]
    END --> CLEAR[로컬 세션 파일 삭제]
```

## 요약
- 호출어 감지 직후 랜덤 인사를 먼저 재생하도록 `serial_voice_proto.py`를 정리했다.
- 종료 멘트(`잘가`, `대화 종료` 등)가 감지되면 `api-server`에 세션 종료를 기록한 뒤 로컬 세션을 닫도록 바꿨다.
- 호출어 이후 질문, 응답, 다시 질문하는 대화 루프는 그대로 유지한다.

## 변경점

### 1. 랜덤 호출어 응답
- `WAKE_GREETINGS`를 추가했다.
- 호출어가 감지되면 먼저 랜덤 인사를 재생한다.
- 호출어 문장 뒤에 덧붙은 tail이 있으면 그 다음에 질문으로 처리한다.

### 2. 세션 종료 저장
- `api_server/services/session_service.py`에 `end_session()`을 추가했다.
- `api_server/routers/sessions.py`에 `POST /sessions/{session_id}/end`를 추가했다.
- 종료 멘트가 감지되면 세션의 `ended_at`을 기록하고 로컬 세션 파일은 비운다.

### 3. 검증
- `python -m py_compile ...` 통과
- `uv run --with fastapi==0.115.6 --with httpx==0.28.1 --with pydantic==2.10.4 --with psycopg[binary]==3.2.3 --with requests==2.32.3 --with pytest==8.3.5 pytest ...`
- 결과: `12 passed`

## 현재 동작
- 호출어 감지
- 랜덤 인사
- 사용자 발화
- 모델 응답
- 반복
- 종료 멘트 감지 시 세션 종료 기록
