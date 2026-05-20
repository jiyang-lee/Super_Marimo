# 네트워크 주소 매트릭스

Super Marimo는 Docker 컨테이너, Windows Bridge, 브라우저, Mini PC가 서로 다른 주소 체계를 사용한다.  
실행 모드마다 헷갈리지 않도록 자주 쓰는 주소를 한 곳에 정리한다.

## 주소 기준

| 서비스 | 포트 | Docker 컨테이너 내부 | Windows Bridge | 브라우저 프론트엔드 | Mini PC |
|---|---:|---|---|---|---|
| db-server | 5432 | `db-server:5432` | - | - | - |
| api-server | 8000 | `api-server:8000` | `http://127.0.0.1:8000` | `http://localhost:8000` | `http://<host-ip>:8000` |
| llm-server | 8000 | `llm-server:8000` | `http://127.0.0.1:8001` | - | `http://<host-ip>:8001` |
| voice-server | 8000 | `voice-server:8000` | `http://127.0.0.1:8002` | - | `http://<host-ip>:8002` |
| voice-agent | 8000 | `voice-agent:8000` | `http://127.0.0.1:8003` | `http://localhost:8003` | `http://<host-ip>:8003` |

## 주소 규칙

1. Docker 컨테이너끼리는 서비스 이름을 쓴다.
2. Windows Bridge는 호스트 루프백(`127.0.0.1`)을 쓴다.
3. 브라우저 프론트엔드는 `localhost`를 쓴다.
4. Mini PC나 다른 외부 장비는 호스트 PC의 실제 IP를 쓴다.

## 환경 파일 역할

- `.env.mock`, `.env.cpu`, `.env.gpu`는 컨테이너 내부 주소와 모델 실행 모드를 정한다.
- `.env.local`은 Windows Bridge와 로컬 프론트엔드용 호스트 주소를 정한다.
