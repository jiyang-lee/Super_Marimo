# API Server

`api-server`는 대화 세션과 상호작용 로그를 PostgreSQL에 저장하는 계층입니다.

## 역할
- `llm-server`로 질문 전달
- `session` / `session_message` 저장
- `interaction_log` 저장
- 센서 데이터 저장 및 조회

## 주요 API
- `GET /health`
- `POST /ask`
- `POST /voice/ask`
- `GET /sessions`

## 메모
- DB 스키마는 서버 시작 시 자동 생성한다.
- 실제 저장 책임은 이 서비스가 가진다.
