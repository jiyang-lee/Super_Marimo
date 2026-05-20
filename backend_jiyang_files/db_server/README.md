# DB Server

`db-server`는 root `docker-compose.yml`에서 사용하는 PostgreSQL 컨테이너 정의를 설명하는 자리입니다.

## 역할
- `api-server`의 영속 저장소
- `session`, `session_message`, `sensor_readings`, `interaction_log` 보관

## 메모
- 실제 런타임은 루트 compose가 관리한다.
- 초기 스키마는 `api-server` 시작 시 생성한다.
