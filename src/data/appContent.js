export const navigationItems = [
  { key: "home", label: "홈", icon: "🏠" },
  { key: "sensor", label: "센서", icon: "🌿" },
  { key: "chat", label: "채팅", icon: "💬" },
  { key: "settings", label: "설정", icon: "⚙️" },
];

export const homeNotices = [
  "화면 구조를 먼저 잡아두고, 이미지는 나중에 차근차근 연결합니다.",
  "이미지는 역할별 폴더로 나눠서 관리하면 나중에 찾기 쉬워요.",
  "폴더명과 파일명은 초보자도 바로 이해할 수 있게 단순하게 유지합니다.",
];

export const questItems = [
  {
    icon: "💧",
    title: "물 상태 확인",
    description: "수위가 안정적인지 한 번 눌러서 표시합니다.",
  },
  {
    icon: "🫧",
    title: "병 상태 확인",
    description: "깨끗한 환경인지 점검하는 버튼입니다.",
  },
  {
    icon: "☀️",
    title: "햇빛 확인",
    description: "조도가 적절한지 바로 표시할 수 있게 합니다.",
  },
  {
    icon: "♥",
    title: "사랑 주기",
    description: "마리모에게 오늘의 한마디를 남기는 용도입니다.",
  },
];

export const weeklyRows = [
  ["06:00", "23°C", "49%", "82%", "280 lux"],
  ["09:00", "24°C", "47%", "81%", "410 lux"],
  ["12:00", "25°C", "45%", "80%", "620 lux"],
  ["15:00", "24°C", "48%", "79%", "540 lux"],
  ["18:00", "23°C", "52%", "80%", "360 lux"],
  ["21:00", "22°C", "55%", "81%", "240 lux"],
];

export const sensorRows = [
  {
    title: "온도",
    value: "24°C",
    note: "마리모가 편안하게 느끼는 범위를 표시합니다.",
  },
  {
    title: "습도",
    value: "45%",
    note: "주변 공기 상태를 쉽게 확인할 수 있습니다.",
  },
  {
    title: "수위",
    value: "80%",
    note: "물 높이가 충분한지 한눈에 볼 수 있습니다.",
  },
  {
    title: "조도",
    value: "500 lux",
    note: "빛이 너무 강하거나 약하지 않은지 체크합니다.",
  },
];

export const guideItems = [
  {
    title: "직관적인 폴더명",
    text: "components, pages, data, styles처럼 뜻이 바로 보이는 이름만 씁니다.",
  },
  {
    title: "이미지 보관 규칙",
    text: "새 이미지는 public/images/incoming에 먼저 넣고, 나중에 역할별 폴더로 옮깁니다.",
  },
  {
    title: "주석 규칙",
    text: "무엇을 하는지와 왜 필요한지, 초보자가 읽어도 알 수 있도록 자세히 적습니다.",
  },
  {
    title: "백엔드 분리",
    text: "이번 준비 단계에서는 백엔드 파일을 건드리지 않고 프론트만 정리합니다.",
  },
];

export const settingsItems = [
  {
    title: "이미지 경로 안내",
    description: "새로 만든 이미지를 어디에 둘지 확인합니다.",
    modalType: "guide",
  },
  {
    title: "센서 구조 안내",
    description: "센서 카드와 이력 테이블의 역할을 설명합니다.",
    modalType: "sensor",
  },
];

export const chatStarterMessages = [
  {
    id: "bot-1",
    role: "bot",
    text: "안녕! 무엇을 도와줄까?",
    time: "14:31",
  },
  {
    id: "user-1",
    role: "user",
    text: "오늘 마리모 상태는 어때?",
    time: "14:32",
  },
  {
    id: "bot-2",
    role: "bot",
    text: "지금은 무난해요. 조금 더 안정적으로 자라는 중이에요.",
    time: "14:32",
  },
];
