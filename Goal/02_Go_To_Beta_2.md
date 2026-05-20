# 베타 버전으로 가는길 2: 보완

이전 정리가 **“베타버전으로 가는 길”**이었다면, 이번 정리는 그 다음 단계인 **“베타로 올리기 전에 반드시 안정화해야 할 항목”**이다.

현재 레포는 전체 방향이 잘못된 상태는 아니다. 오히려 `api-server`, `llm-server`, `voice-server`, `voice-agent`, `bridge`, `db-server`로 역할이 나뉘어 있어 구조는 꽤 명확하다.

다만 지금 상태 그대로 베타에 들어가면 **실행 환경 문제, 이벤트 중복 저장, 모델 로딩 실패, 실제 스피커 재생 확인 문제**에서 막힐 가능성이 높다.

---

# 1. 실행 모드 분리

## 중요도: 최상

현재는 `llm-server`와 `voice-server`가 실제 GPU 모델을 기본으로 실행하는 구조에 가깝다.

이 상태에서는 GPU 설정, CUDA, Docker GPU 연결, 모델 다운로드 상태에 따라 전체 서비스가 쉽게 멈출 수 있다.

베타 전에는 실행 모드를 반드시 나눠야 한다.

## 수정 방향

개발과 테스트 단계에서는 전체 기능 흐름을 먼저 검증할 수 있어야 한다.

따라서 다음처럼 모드를 분리한다.

| 모드 | 목적 |
| --- | --- |
| Mock 모드 | DB 저장, API 연결, 프론트 테스트, 이벤트 흐름 검증 |
| CPU 모드 | GPU 없이 최소 기능 테스트 |
| GPU 모드 | 실제 LLM, STT, TTS 모델 실행 |

## 왜 중요한가

베타 테스트에서 가장 먼저 확인해야 하는 것은 모델 성능이 아니라 **전체 시스템 흐름이 끊기지 않는지**이다.

즉, 처음부터 실제 모델을 무겁게 올리는 것보다 다음 흐름이 정상인지 먼저 봐야 한다.

```
센서 입력
→ API 서버 수신
→ DB 저장
→ 이벤트 생성
→ voice-agent 감지
→ TTS 요청
→ audio 파일 생성
→ bridge 재생
```

이 흐름이 Mock 모드에서도 돌아가야 한다.

---

# 2. LLM / Voice 서버 healthcheck 분리

## 중요도: 최상

현재 구조에서는 `/health` 확인 과정에서 모델 로딩까지 같이 일어날 가능성이 있다.

이러면 단순히 서버가 살아있는지 확인하려는 healthcheck가 너무 무거워진다.

## 문제 상황

서비스 실행 시 다음 문제가 생길 수 있다.

```
docker compose up
→ healthcheck 실행
→ LLM 모델 로딩 시작
→ 모델 다운로드 또는 GPU 로딩 지연
→ healthcheck timeout
→ unhealthy 처리
→ voice-agent가 뜨지 않음
```

이건 베타 단계에서 매우 치명적이다.

## 수정 방향

상태 확인 API를 분리한다.

| 엔드포인트 | 역할 |
| --- | --- |
| `/health` | 서버 프로세스가 살아있는지만 확인 |
| `/ready` | 모델까지 정상 로딩됐는지 확인 |

Docker Compose의 healthcheck는 `/health`만 보게 한다.

모델 준비 여부는 별도로 `/ready`에서 확인한다.

## 기대 효과

서비스가 일단 뜬 뒤, 모델 준비 상태를 따로 확인할 수 있다.

이렇게 하면 모델 로딩이 조금 늦어도 전체 컨테이너 구성이 무너지는 문제를 줄일 수 있다.

---

# 3. Sensor Warning 이벤트 폭주 방지

## 중요도: 최상

Wemos 거리센서는 반복적으로 값을 보낸다.

사람이 센서 가까이에 계속 있으면 `sensor_warning` 이벤트가 계속 저장될 수 있다.

## 문제 상황

예를 들어 1초마다 센서값을 보낸다면 다음처럼 DB가 쌓일 수 있다.

```
sensor_warning
sensor_warning
sensor_warning
sensor_warning
sensor_warning
...
```

현재 `proactive_greeting`에는 쿨다운이 있지만, `sensor_warning` 자체에도 제한이 필요하다.

## 수정 방향

`proactive_greeting`뿐 아니라 `sensor_warning`에도 저장 쿨다운을 둔다.

추천 기준은 다음과 같다.

| 이벤트 | 추천 쿨다운 |
| --- | --- |
| sensor_warning | 3~5초 |
| proactive_greeting | 60초 이상 |

또한 가능하면 `device_id` 기준으로 쿨다운을 분리한다.

```
같은 Wemos에서 발생한 sensor_warning은 5초에 1번만 저장
proactive_greeting은 60초에 1번만 생성
```

## 기대 효과

DB가 불필요하게 커지는 것을 막을 수 있다.

또한 이벤트 로그를 봤을 때 실제 의미 있는 이벤트만 남게 된다.

---

# 4. 실제 재생 상태와 TTS 생성 상태 분리

## 중요도: 높음

현재 구조에서는 `voice-agent`가 TTS 파일을 생성한 뒤 이벤트를 `played`로 표시하는 흐름에 가깝다.

하지만 실제 스피커 재생은 Windows Bridge의 audio player가 수행한다.

즉, 현재는 다음 두 상태가 섞일 수 있다.

```
TTS 파일 생성 완료
=
스피커 재생 완료
```

하지만 실제로는 다르다.

```
TTS 파일 생성 완료
≠
스피커 재생 완료
```

## 수정 방향

이벤트 상태를 하나의 `played` 값으로만 처리하지 말고, 단계별 상태로 나누는 것이 좋다.

추천 상태는 다음과 같다.

| 상태 | 의미 |
| --- | --- |
| pending | 이벤트 생성됨 |
| tts_generated | TTS 파일 생성됨 |
| playing | Bridge가 재생 시작 |
| played | 실제 재생 완료 |
| failed | 생성 또는 재생 실패 |

## 기대 효과

나중에 문제가 생겼을 때 원인을 정확히 알 수 있다.

예를 들어 다음을 구분할 수 있다.

```
TTS 생성 실패
파일은 생성됐지만 Bridge가 감지 못함
Bridge는 감지했지만 스피커 재생 실패
재생은 됐지만 DB에 반영 안 됨
```

베타 테스트에서는 이런 디버깅 정보가 매우 중요하다.

---

# 5. Docker Compose 파일 분리

## 중요도: 높음

현재 하나의 `docker-compose.yml` 안에 실제 운영에 가까운 설정이 많이 들어가 있다.

하지만 베타 전에는 테스트 목적에 따라 compose를 분리하는 것이 좋다.

## 수정 방향

다음처럼 구성한다.

```
docker-compose.yml
docker-compose.mock.yml
docker-compose.gpu.yml
docker-compose.dev.yml
```

각 파일의 역할은 다음과 같다.

| 파일 | 목적 |
| --- | --- |
| docker-compose.yml | 공통 기본 구조 |
| docker-compose.mock.yml | 모델 없이 흐름 테스트 |
| docker-compose.gpu.yml | 실제 GPU 모델 실행 |
| docker-compose.dev.yml | 로컬 개발용 포트, 볼륨 설정 |

## 기대 효과

상황별 실행 명령이 명확해진다.

예를 들어:

```
가볍게 전체 흐름 테스트
→ mock compose 실행

실제 음성 모델 테스트
→ gpu compose 실행

프론트와 API 연결 테스트
→ dev compose 실행
```

이렇게 나누면 팀원이 봐도 훨씬 이해하기 쉽다.

---

# 6. 환경변수 정리

## 중요도: 높음

현재 DB 정보, 모델명, threshold, cooldown, 포트 설정 등이 compose나 config에 직접 들어가 있다.

초기 개발에는 괜찮지만, 베타에서는 설정값을 쉽게 바꿀 수 있어야 한다.

## 수정 방향

`.env` 파일을 목적별로 나눈다.

```
.env.mock
.env.dev
.env.gpu
.env.local
```

정리해야 할 주요 값은 다음과 같다.

| 설정 | 예시 |
| --- | --- |
| DB 주소 | DATABASE_URL |
| LLM 서버 주소 | LLM_SERVER_URL |
| Voice 서버 주소 | VOICE_SERVER_URL |
| 거리 임계값 | SENSOR_WARNING_DISTANCE_THRESHOLD_CM |
| 선제 인사 쿨다운 | PROACTIVE_GREETING_COOLDOWN_SECONDS |
| STT 모델 크기 | STT_MODEL_SIZE |
| TTS 백엔드 | TTS_BACKEND |
| 공유 오디오 폴더 | SHARED_AUDIO_DIR |

## 기대 효과

코드를 수정하지 않고도 테스트 조건을 바꿀 수 있다.

예를 들어 거리센서 기준을 10cm에서 20cm로 바꿀 때 코드 수정 없이 `.env`만 수정하면 된다.

---

# 7. Bridge와 서버 주소 설정 정리

## 중요도: 중간 이상

Bridge는 Windows host에서 실행되고, 나머지 서버들은 Docker 컨테이너로 실행된다.

이 구조에서는 주소 설정이 매우 중요하다.

## 문제 상황

Bridge 입장에서는 컨테이너 내부 주소인 `http://voice-server:8000`을 사용할 수 없다.

Bridge는 Windows에서 실행되기 때문에 host 기준 주소를 써야 한다.

예를 들어:

```
voice-agent → http://127.0.0.1:8003
voice-server → http://127.0.0.1:8002
api-server → http://127.0.0.1:8000
```

반면 컨테이너끼리는 다음 주소를 사용한다.

```
voice-agent → http://voice-server:8000
api-server → http://llm-server:8000
```

## 수정 방향

문서에 주소 기준을 명확히 적어야 한다.

```
컨테이너 내부 통신 주소
Windows Bridge에서 접근하는 주소
프론트엔드에서 접근하는 주소
Mini PC에서 접근하는 주소
```

이 네 가지를 분리해서 정리한다.

## 기대 효과

실행할 때 “왜 8000인데 안 되지?”, “왜 8002로 열었는데 컨테이너 안에서는 8000이지?” 같은 혼란을 줄일 수 있다.

---

# 8. 이벤트 로그 정리 기준 추가

## 중요도: 중간

현재 이벤트 종류는 꽤 잘 나뉘어 있다.

```
wakeword
speech_started
speech_ended
stt_completed
llm_completed
tts_played
sensor_warning
proactive_greeting
manual_test
```

다만 베타 테스트에서는 이벤트가 많아질 수 있기 때문에 로그 정리 기준이 필요하다.

## 수정 방향

이벤트별 보존 기간을 정한다.

| 데이터 | 추천 보존 기간 |
| --- | --- |
| realtime sensor_readings | 7일 |
| hourly sensor_readings | 장기 보존 가능 |
| speech_started / speech_ended | 짧게 보존 |
| interaction_log | 장기 보존 가능 |
| proactive_greeting | 중기 보존 |
| manual_test | 필요 시 삭제 |

## 기대 효과

DB가 불필요하게 커지는 것을 막고, 나중에 분석에 필요한 데이터만 남길 수 있다.

---

# 9. README 실행 가이드 보강

## 중요도: 중간

README의 전체 흐름 설명은 좋다.

하지만 베타로 넘어가려면 “어떤 순서로 실행해야 하는지”가 더 명확해야 한다.

## 수정 방향

README에 다음 섹션을 추가한다.

```
1. Mock 모드로 전체 흐름 테스트
2. DB 정상 확인
3. API 서버 healthcheck 확인
4. Voice Agent healthcheck 확인
5. 거리센서 이벤트 수동 테스트
6. Bridge 실행
7. RP2040 시리얼 연결 테스트
8. 실제 STT / TTS / LLM 모델 테스트
```

각 단계마다 확인해야 할 URL도 적는다.

```
http://localhost:8000/health
http://localhost:8001/health
http://localhost:8002/health
http://localhost:8003/health
```

## 기대 효과

나중에 실행 순서를 까먹어도 README만 보고 재현할 수 있다.

베타 테스트를 다른 사람이 도와줄 때도 훨씬 수월해진다.

---

# 10. 실패 상황별 에러 메시지 정리

## 중요도: 중간

현재 여러 서비스가 나뉘어 있기 때문에, 문제가 생기면 어디서 실패했는지 빠르게 알아야 한다.

## 수정 방향

대표 실패 상황을 정리한다.

| 실패 상황 | 확인 위치 |
| --- | --- |
| DB 연결 실패 | api-server 로그 |
| LLM 응답 없음 | llm-server 로그 |
| STT 결과 없음 | voice-server 로그 |
| TTS 파일 생성 실패 | voice-agent 또는 voice-server 로그 |
| TTS 파일은 있는데 소리 안 남 | bridge audio_player |
| 센서값은 오는데 인사 안 함 | api-server sensor policy |
| 이벤트는 있는데 재생 안 됨 | voice-agent event poller / bridge |

## 기대 효과

베타 테스트 중 문제가 생겼을 때 원인을 빠르게 좁힐 수 있다.

---

# 베타 전 최종 우선순위 요약

| 순위 | 항목 | 중요도 |
| --- | --- | --- |
| 1 | 실행 모드 분리 | 최상 |
| 2 | LLM / Voice 서버 healthcheck 분리 | 최상 |
| 3 | Sensor Warning 이벤트 폭주 방지 | 최상 |
| 4 | 실제 재생 상태와 TTS 생성 상태 분리 | 높음 |
| 5 | Docker Compose 파일 분리 | 높음 |
| 6 | 환경변수 정리 | 높음 |
| 7 | Bridge와 서버 주소 설정 정리 | 중간 이상 |
| 8 | 이벤트 로그 정리 기준 추가 | 중간 |
| 9 | README 실행 가이드 보강 | 중간 |
| 10 | 실패 상황별 에러 메시지 정리 | 중간 |

---

# 최종 정리

지금 레포는 베타로 갈 수 있는 기본 구조는 이미 갖추고 있다.

다만 베타 단계에서 중요한 것은 “기능이 한 번 되는 것”이 아니라 **계속 안정적으로 재현되는 것**이다.

그래서 지금 가장 먼저 해야 할 일은 새 기능을 더 넣는 것이 아니다.

```
무겁게 돌아가는 실제 모델 실행 구조를 가볍게 테스트할 수 있게 만들고,
센서 이벤트가 폭주하지 않게 막고,
TTS 생성과 실제 재생 상태를 분리하고,
실패했을 때 어디서 터졌는지 바로 알 수 있게 만드는 것
```

이 네 가지가 베타 진입 전 핵심이다.