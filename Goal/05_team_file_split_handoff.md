# Super Marimo 팀 작업 분할

## 목적

현재 프론트 작업을 두 로컬로 나눠서 진행한다.

- 팀 A: `Home`, `Sensor`, `Settings`
- 팀 B: `Lab`, `Report`

충돌을 줄이기 위해, 각 팀이 손대는 파일을 미리 고정한다.

## 팀 A 담당

- `frontend/src/pages/HomePage.tsx`
- `frontend/src/pages/SensorPage.tsx`
- `frontend/src/pages/SettingsPage.tsx`
- `frontend/src/components/MarimoImage.tsx`
- `frontend/src/pages/HomePage` 관련 스타일 블록
- `frontend/src/pages/SensorPage` 관련 스타일 블록
- `frontend/src/pages/SettingsPage` 관련 스타일 블록

## 팀 B 담당

- `frontend/src/pages/LabPage.tsx`
- `frontend/src/pages/ReportPage.tsx`
- `frontend/src/pages/DashboardPage.tsx`
- `frontend/src/pages/EventsPage.tsx`
- `frontend/src/pages/TestPage.tsx`
- `frontend/src/pages/LabPage` 관련 스타일 블록
- `frontend/src/pages/ReportPage` 관련 스타일 블록
- `frontend/src/pages/DashboardPage` 관련 스타일 블록
- `frontend/src/pages/EventsPage` 관련 스타일 블록
- `frontend/src/pages/TestPage` 관련 스타일 블록

## 공용 잠금 파일

아래 파일은 두 팀이 동시에 만지지 않는다.

- `frontend/src/api.ts`
- `frontend/src/App.tsx`
- `frontend/src/components/Layout.tsx`
- `frontend/src/main.tsx`
- `frontend/src/index.css`

## 작업 원칙

- 각 팀은 자기 담당 파일만 수정한다.
- 공용 잠금 파일은 필요할 때만 한 번에 정리한다.
- Home/Sensor/Settings 팀과 Lab/Report 팀이 같은 CSS 블록을 건드려야 하면, 먼저 담당을 합의하고 수정한다.
- 백엔드 계약 파일인 `frontend/src/api.ts`는 이번 분할에서 건드리지 않는다.

## 권장 순서

1. 팀 A가 `Home`, `Sensor`, `Settings` 화면 수정을 먼저 마무리한다.
2. 팀 B가 `Lab`, `Report` 화면을 병행한다.
3. 공용 파일은 마지막에 한 번만 정리한다.

