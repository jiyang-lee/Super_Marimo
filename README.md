# MARIMO QUEST

마리모를 돌보는 반응형 웹앱입니다.  
현재 기준은 React + Vite 프론트 구조입니다.

## 현재 기준

- 화면은 `src/` 아래의 React 코드가 기준입니다.
- 옛 정적 `css/`, `js/` 구조는 사용하지 않습니다.
- 이미지는 `public/images/` 아래에서 관리합니다.
- 새 이미지는 먼저 `public/images/incoming/`에 넣어두고, 화면 연결할 때 역할별 폴더로 옮깁니다.

## 폴더 역할

- `src/`
  - 화면 컴포넌트와 데이터, 스타일이 들어갑니다.
- `public/images/incoming/`
  - 새 이미지를 잠시 모아두는 임시 폴더입니다.
- `public/images/logo/`
  - 로고와 파비콘을 넣습니다.
- `public/images/character/`
  - 마리모 캐릭터 이미지를 넣습니다.
- `public/images/home/`
  - 홈 화면 배경과 대표 이미지를 넣습니다.
- `public/images/chat/`
  - 채팅 아바타 이미지를 넣습니다.
- `public/images/sensor/`
  - 센서 아이콘을 넣습니다.
- `public/images/settings/`
  - 설정 화면 아이콘을 넣습니다.
- `public/images/common/`
  - 로딩, 빈 상태, 에러 안내 이미지를 넣습니다.

## 실행 방법

1. 이 폴더에서 `npm install`을 한 번 실행합니다.
2. `npm run dev`로 개발 화면을 엽니다.
3. 필요하면 `npm run build`로 배포용 파일도 확인합니다.

## 작업 규칙

- 폴더명과 파일명은 초보자도 바로 이해할 수 있게 직관적으로 씁니다.
- 주석은 무엇을 하는지와 왜 필요한지를 함께 적습니다.
- 백엔드는 이번 작업 범위에서 제외합니다.
