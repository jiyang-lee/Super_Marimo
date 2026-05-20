# Super_Marimo 프론트엔드-백엔드 연결 상태 보고서

- 작업 기준 경로: `C:\Projects\_active\Super_Marimo_backend_ui_merge`
- 기준 브랜치: `codex/backend-jiyang-ui-merge`
- 문서 목적: 다른 에이전트가 현재 프론트엔드와 백엔드의 연결 상태를 빠르게 이해하고, 어느 화면이 어떤 서비스와 붙어 있는지 바로 이어받을 수 있게 정리한다.

## 1. 문서 목적과 대상

이 문서는 현재 통합 worktree 기준의 프론트엔드-백엔드 연결 상태 설명서다.

대상 독자는 다음과 같다.

- 이 저장소를 이어받아 프론트 작업을 계속할 에이전트
- 백엔드 계약을 바꾸기 전에 프론트 영향 범위를 확인해야 하는 에이전트
- 운영용 화면(`Chat`, `Sensor`, `Settings`, `Lab`)이 실제로 어떤 서비스와 연결되는지 빠르게 확인하려는 에이전트

이 문서는 구현 제안서가 아니라 인수인계용 상태 설명서다. 따라서 “지금 무엇이 연결되어 있는지”, “화면별로 무엇이 실제 동작하는지”, “어떤 주의점이 남아 있는지”에 집중한다.

## 2. 전체 연결 구조 요약

현재 프론트는 브라우저에서 직접 `api_server`, `voice_agent`, `voice_server`, `llm_server`에 붙지 않는다. Vite dev server 프록시를 통해 다음 경로로 접근한다.

- `/api` -> `api_server` (`http://localhost:8000`)
- `/agent` -> `voice_agent` (`http://localhost:8003`)
- `/voice` -> `voice_server` (`http://localhost:8002`)
- `/llm` -> `llm_server` (`http://localhost:8001`)

실제 프록시 설정은 [vite.config.ts](C:/Projects/_active/Super_Marimo_backend_ui_merge/frontend/vite.config.ts)에 있다.

프론트의 공용 호출 진입점은 [api.ts](C:/Projects/_active/Super_Marimo_backend_ui_merge/frontend/src/api.ts) 하나로 모여 있다. 각 화면은 이 파일의 래퍼 함수를 import해서 쓴다.

## 3. 프론트 기본 프록시 구조

`frontend/src/api.ts`에는 현재 다음 공용 API 래퍼가 있다.

- 헬스체크
  - `checkAgentHealth`
  - `checkApiHealth`
  - `checkVoiceHealth`
  - `checkLlmHealth`

- 세션/대화
  - `listSessions`
  - `getSessionDetail`
  - `deleteSession`
  - `askChat`
  - `askAgent`

- 센서/런타임 설정
  - `getLatestSensor`
  - `getSensorHistory`
  - `getRuntimeSettings`
  - `updateRuntimeSettings`
  - `getRuntimeSettingsHistory`
  - `ingestRealtimeSensor`

- 이벤트/TTS
  - `listEvents`
  - `markEventPlayed`
  - `synthesizeTts`

실제 prefix는 다음과 같다.

- `AGENT = /agent`
- `API = /api`
- `VOICE = /voice`
- `LLM = /llm`

즉, 프론트는 화면별로 각기 다른 fetch URL을 직접 만들지 않고, 이 래퍼 계층을 통해 공통 응답 처리와 오류 처리를 공유한다.

## 4. 화면별 연결 상태

### 4.1 Home

- 파일: [HomePage.tsx](C:/Projects/_active/Super_Marimo_backend_ui_merge/frontend/src/pages/HomePage.tsx)
- 역할: `frontend/jeong` 테마를 시각적으로 보여주는 홈 화면
- 백엔드 직접 호출: 없음

현재 Home은 이미지, 배경, 퀘스트 보드, 말풍선 중심의 시각 테마 화면이다. 런타임 데이터는 직접 읽지 않는다.

### 4.2 Chat

- 파일: [ChatPage.tsx](C:/Projects/_active/Super_Marimo_backend_ui_merge/frontend/src/pages/ChatPage.tsx)
- 사용 함수:
  - `askChat`
  - `listSessions`
  - `getSessionDetail`
  - `deleteSession`
  - `synthesizeTts`
  - `updateRuntimeSettings`

Chat은 실제 운영 대화 화면이다. 주요 동작은 다음과 같다.

- 세션 목록 조회
- 세션 상세 메시지 조회
- 질문 전송
- 세션 삭제
- TTS 재생
- 새 세션 시작 시 일부 런타임 설정 보정

대화 요청은 `/api/ask` 경로로 들어가며, 내부적으로는 `api_server`가 센서 문맥과 세션 상태를 포함해 처리한다.

### 4.3 Sensor

- 파일: [SensorPage.tsx](C:/Projects/_active/Super_Marimo_backend_ui_merge/frontend/src/pages/SensorPage.tsx)
- 사용 함수:
  - `getLatestSensor`
  - `getSensorHistory`

Sensor는 최신 센서 스냅샷과 이력 그래프를 보여주는 화면이다. 이 페이지는 백엔드에서 계산된 최신값과 저장된 이력을 주기적으로 polling해서 렌더링한다.

### 4.4 Settings

- 파일: [SettingsPage.tsx](C:/Projects/_active/Super_Marimo_backend_ui_merge/frontend/src/pages/SettingsPage.tsx)
- 사용 함수:
  - `getRuntimeSettings`
  - `updateRuntimeSettings`

Settings는 현재 다음 런타임 설정을 읽고 바꾼다.

- `web_voice_enabled`
- `wake_enabled`
- `distance_detection_enabled`
- `distance_threshold_cm`

즉, 이 화면은 단순 UI가 아니라 실제 런타임 상태를 읽고 쓰는 운영용 화면이다.

### 4.5 Lab

- 파일: [LabPage.tsx](C:/Projects/_active/Super_Marimo_backend_ui_merge/frontend/src/pages/LabPage.tsx)
- 역할: 운영 콘솔
- 구조: `Dashboard`, `Test`, `Events`를 탭으로 묶은 화면

Lab 자체는 별도 API를 직접 호출하지 않는다. 내부 탭으로 렌더링되는 `DashboardPage`, `TestPage`, `EventsPage`가 실제 연결을 담당한다.

### 4.6 Dashboard

- 파일: [DashboardPage.tsx](C:/Projects/_active/Super_Marimo_backend_ui_merge/frontend/src/pages/DashboardPage.tsx)
- 사용 함수:
  - `checkAgentHealth`
  - `checkApiHealth`
  - `checkVoiceHealth`
  - `checkLlmHealth`
  - `getLatestSensor`
  - `listSessions`
  - `listEvents`

Dashboard는 현재 전체 연결 상태를 한 번에 요약해서 보여주는 운영용 상태판이다.

- 서비스 헬스체크
- 최신 센서값
- 최근 세션
- 최근 이벤트

### 4.7 Events

- 파일: [EventsPage.tsx](C:/Projects/_active/Super_Marimo_backend_ui_merge/frontend/src/pages/EventsPage.tsx)
- 사용 함수:
  - `listEvents`

Events는 이벤트 로그 조회 화면이다. 현재는 목록 조회 중심이고, 필터를 걸어 최근 이벤트를 확인하는 용도에 가깝다.

### 4.8 Test

- 파일: [TestPage.tsx](C:/Projects/_active/Super_Marimo_backend_ui_merge/frontend/src/pages/TestPage.tsx)
- 사용 함수:
  - `askChat`
  - `getLatestSensor`
  - `getRuntimeSettings`
  - `getRuntimeSettingsHistory`
  - `synthesizeTts`
  - `updateRuntimeSettings`

Test는 운영자가 빠르게 기능을 눌러보는 실험용 화면이다.

- 빠른 프롬프트 전송
- 센서 최신값 확인
- 런타임 설정 확인/변경
- 설정 변경 이력 확인
- TTS 직접 재생

### 4.9 Report

- 파일: [ReportPage.tsx](C:/Projects/_active/Super_Marimo_backend_ui_merge/frontend/src/pages/ReportPage.tsx)
- 백엔드 직접 호출: 없음

Report는 현재 연결 상태 설명용 화면이 아니라 시각 테마용 UI다. 따라서 실제 연결 검증은 `Chat`, `Sensor`, `Settings`, `Lab` 기준으로 해야 한다.

## 5. 서비스별 실제 책임

### api_server

현재 프론트와 가장 많이 붙는 핵심 서비스다.

- 세션 조회/상세/삭제
- 센서 latest/history
- 이벤트 조회
- 런타임 설정 조회/수정
- `/ask` 처리

즉, 브라우저 프론트의 대부분의 비즈니스 요청은 `api_server`가 받는다.

### voice_agent

- `/agent/health`
- `/agent/ask`

음성 에이전트 진입점 역할이다. `askAgent`를 쓰는 화면이나 상태 확인에서 이 서비스로 들어간다.

### voice_server

- `/tts`
- `/health`

TTS/STT 관련 상태와 음성 합성 진입점이다. 현재 프론트에서 직접 눈에 띄는 연결은 `synthesizeTts`다.

### llm_server

- 헬스체크 노출
- 내부적으로 `api_server` 또는 `voice_agent`가 호출하는 LLM 생성 경로 담당

프론트는 `llm_server`를 직접 많이 두드리지는 않지만, Dashboard에서 health 확인 대상으로 본다.

## 6. 현재 확인된 주의점

### 6.1 테마 반영 정도

통합 브랜치 기준으로 `frontend/jeong` 테마는 일부 페이지에 강하게 반영됐다. 다만 모든 페이지가 같은 완성도와 동일한 시각 규칙으로 정리된 상태는 아니다.

특히 Home과 공통 배경/헤더 쪽은 `frontend/jeong` 분위기를 많이 가져왔지만, 운영 화면 내부는 기존 `backend/jiyang` 기능 UI를 그대로 안고 있는 부분이 있다.

### 6.2 LabPage의 성격

`LabPage`는 새 운영 콘솔 껍데기이고, 내부 탭은 기존 `Dashboard`, `Test`, `Events`를 그대로 감싼 구조다. 따라서 Lab을 고친다고 해서 내부 세 페이지가 자동으로 구조적으로 통합된 것은 아니다.

### 6.3 인코딩 문제

기존 일부 파일과 문서에는 깨진 한글이 남아 있다. 특히 예전 보고서와 몇몇 UI 파일에 인코딩 문제가 섞여 있으므로, 이후 문서 작성과 텍스트 정리는 깨끗한 한국어 기준으로 다시 하는 편이 좋다.

### 6.4 Report 화면의 역할

현재 `Report` 화면은 프론트-백 연결 설명 화면이 아니다. 따라서 연결 상태를 검증할 때 `Report`를 기준으로 보면 안 된다.

실제 연결 검증 기준 화면은 다음 네 개다.

- `Chat`
- `Sensor`
- `Settings`
- `Lab`

### 6.5 포트 구분

현재 작업 중인 환경에서는 다음처럼 구분해서 보는 것이 맞다.

- `5173`: 원래 브랜치에서 띄운 기존 프론트 dev 서버
- `5174`: 통합 worktree(`codex/backend-jiyang-ui-merge`)에서 띄운 프론트 dev 서버

즉, 통합 브랜치 결과를 볼 때는 `5174`를 기준으로 확인해야 한다.

## 7. 로컬 실행 및 확인 경로

### 백엔드 서비스

저장소 루트에서 백엔드 관련 서비스는 `docker compose` 기준으로 올린다.

```powershell
cd C:\Projects\_active\Super_Marimo_backend_ui_merge
docker compose up --build -d
```

프록시 기준 포트는 다음과 같다.

- `api_server`: `8000`
- `llm_server`: `8001`
- `voice_server`: `8002`
- `voice_agent`: `8003`

### 프론트엔드

```powershell
cd C:\Projects\_active\Super_Marimo_backend_ui_merge\frontend
npm run dev -- --host 0.0.0.0 --port 5174
```

### 확인 라우트

현재 연결 상태를 볼 때 우선 확인할 라우트는 다음과 같다.

- `/chat`
- `/sensor`
- `/settings`
- `/lab`

보조 확인 라우트는 다음과 같다.

- `/`
- `/report`

## 8. 결론

현재 프론트는 공통 API 래퍼(`frontend/src/api.ts`)를 중심으로 `api_server`, `voice_agent`, `voice_server`, `llm_server`와 연결된다. 이 중 실제 운영 기능 대부분은 `api_server`가 중심이고, `voice_agent`와 `voice_server`는 음성 흐름을 보조한다.

즉, 지금 상태를 이어받는 에이전트는 먼저 `frontend/src/api.ts`와 `Chat`, `Sensor`, `Settings`, `Lab` 네 화면을 보면 된다. 이 네 군데를 이해하면 현재 프론트-백 연결 구조의 대부분을 빠르게 파악할 수 있다.
