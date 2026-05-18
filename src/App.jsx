import React, { useEffect, useState } from "react";

const screens = [
  { key: "home", label: "Home" },
  { key: "sensor", label: "Sensor" },
  { key: "chat", label: "Chat" },
  { key: "settings", label: "Settings" },
];

const weeklySummaries = [
  {
    range: "05.18.~05.24.",
    text: "온도 : 23.5도, 습도 : 49%, 수위 : 81%, 조도 : 408lux",
    note: "이번 주는 물 상태가 안정적이었어요.",
  },
  {
    range: "05.25.~05.31.",
    text: "온도 : 25.7도, 습도 : 54%, 수위 : 84%, 조도 : 700lux",
    note: "조도가 조금 올라간 주간이에요.",
  },
  {
    range: "06.01.~06.07.",
    text: "온도 : 24.2도, 습도 : 51%, 수위 : 83%, 조도 : 1,120lux",
    note: "전체 센서 수치가 고르게 유지됐어요.",
  },
  {
    range: "06.08.~06.14.",
    text: "온도 : 24.8도, 습도 : 52%, 수위 : 82%, 조도 : 860lux",
    note: "주중과 주말 변화가 작았어요.",
  },
];

const hourlyHistory = [
  ["09:00", "온도 24도, 습도 47%, 수위 81%, 조도 410 lux"],
  ["12:00", "온도 25도, 습도 45%, 수위 80%, 조도 620 lux"],
  ["15:00", "온도 24도, 습도 48%, 수위 79%, 조도 540 lux"],
  ["18:00", "온도 23도, 습도 52%, 수위 80%, 조도 360 lux"],
];

const monthLabels = [
  "1월",
  "2월",
  "3월",
  "4월",
  "5월",
  "6월",
  "7월",
  "8월",
  "9월",
  "10월",
  "11월",
  "12월",
];

const chatMessages = [
  { id: 1, from: "marimo", text: "안녕! 오늘 센서 상태부터 살펴볼까?" },
  { id: 2, from: "user", text: "좋아, 순서대로 다시 확인해보자." },
  { id: 3, from: "marimo", text: "좋아. 홈부터 센서, 채팅, 설정 순서로 복구하면 돼." },
];

export default function App() {
  const [activeScreen, setActiveScreen] = useState("home");
  const [sensorView, setSensorView] = useState("weekly");
  const [activeMonth, setActiveMonth] = useState("5월");

  useEffect(() => {
    document.getElementById("fallback-root")?.remove();
  }, []);

  return (
    <div style={shellStyle}>
      <header style={headerStyle}>
        <div>
          <div style={brandStyle}>MARIMO QUEST</div>
          <div style={subtitleStyle}>마리모를 돌보는 반응형 웹앱</div>
        </div>

        <nav style={navStyle} aria-label="주요 화면 이동">
          {screens.map((screen) => (
            <button
              key={screen.key}
              type="button"
              onClick={() => setActiveScreen(screen.key)}
              style={navButtonStyle(activeScreen === screen.key)}
            >
              {screen.label}
            </button>
          ))}
        </nav>
      </header>

      <main style={mainStyle}>
        {activeScreen === "home" && (
          <section style={gridThreeStyle}>
            <Panel title="공지사항" chip="초보자용">
              <p style={leadStyle}>
                지금은 홈 구조를 다시 정리한 상태예요. 아래 3개 카드가 보이면 정상입니다.
              </p>
              <ul style={listStyle}>
                <li style={listItemStyle}>왼쪽: 공지사항</li>
                <li style={listItemStyle}>가운데: 전체 마리모 이미지</li>
                <li style={listItemStyle}>오른쪽: 오늘의 퀘스트</li>
              </ul>
            </Panel>

            <Panel title="전체 마리모 이미지">
              <div style={imageSlotStyle}>
                <strong style={imageStrongStyle}>이미지 자리</strong>
                <span style={mutedStyle}>나중에 마리모 전체 이미지를 넣을 위치예요.</span>
              </div>
            </Panel>

            <Panel title="오늘의 퀘스트" chip="DAY 01">
              <div style={questItemStyle}>
                <strong>물 상태 확인</strong>
                <span style={mutedStyle}>수위가 적정한지 먼저 살펴보세요.</span>
              </div>
              <div style={questItemStyle}>
                <strong>온도 상태 확인</strong>
                <span style={mutedStyle}>마리모가 지내기 좋은 온도인지 봐주세요.</span>
              </div>
            </Panel>
          </section>
        )}

        {activeScreen === "sensor" && (
          <section style={screenStackStyle}>
            <div style={sensorHeroGridStyle}>
              <Panel title="마리모 이미지" chip="캐릭터">
                <div style={avatarSlotStyle}>
                  <strong style={imageStrongStyle}>전체 마리모 이미지</strong>
                  <span style={mutedStyle}>
                    왼쪽에는 나중에 전체 마리모 캐릭터 이미지를 넣을 수 있어요.
                  </span>
                </div>
              </Panel>

              <Panel title="현재 센서 상태" chip="실시간">
                <div style={sensorGridStyle}>
                  {[
                    ["온도", "24.0도"],
                    ["습도", "45%"],
                    ["수위", "80%"],
                    ["조도", "500 lux"],
                  ].map(([label, value]) => (
                    <div key={label} style={sensorCardStyle}>
                      <span style={mutedStyle}>{label}</span>
                      <strong style={sensorValueStyle}>{value}</strong>
                    </div>
                  ))}
                </div>
                <p style={leadStyle}>
                  현재 값은 예시예요. 실제 센서가 연결되면 이 숫자만 자동으로 바뀌게 됩니다.
                </p>
              </Panel>
            </div>

            <Panel title="시간별 센서 이력" chip="기록">
              <div style={historyBoxStyle}>
                {hourlyHistory.map(([time, text]) => (
                  <div key={time} style={historyRowStyle}>
                    <strong>{time}</strong>
                    <span style={mutedStyle}>{text}</span>
                  </div>
                ))}
              </div>
            </Panel>

            <Panel title="위클릭 / 머슬릭 자료" chip="주간 / 월간">
              <div style={modeSwitchStyle}>
                <button
                  type="button"
                  onClick={() => setSensorView("weekly")}
                  style={modeButtonStyle(sensorView === "weekly")}
                >
                  위클릭
                </button>
                <button
                  type="button"
                  onClick={() => setSensorView("monthly")}
                  style={modeButtonStyle(sensorView === "monthly")}
                >
                  머슬릭
                </button>
              </div>

              {sensorView === "weekly" ? (
                <div style={weeklyListStyle}>
                  {weeklySummaries.map((week) => (
                    <div key={week.range} style={weeklyCardStyle}>
                      <strong style={weeklyTitleStyle}>{week.range}</strong>
                      <div style={weeklyTextStyle}>{week.text}</div>
                      <div style={weeklyNoteStyle}>{week.note}</div>
                    </div>
                  ))}
                </div>
              ) : (
                <div style={monthlyLayoutStyle}>
                  <div style={monthGridStyle}>
                    {monthLabels.map((month) => (
                      <button
                        key={month}
                        type="button"
                        onClick={() => setActiveMonth(month)}
                        style={monthButtonStyle(activeMonth === month)}
                      >
                        {month}
                      </button>
                    ))}
                  </div>

                  <div style={graphBoxStyle}>
                    <div style={graphHeaderStyle}>
                      <strong>{activeMonth} 그래프</strong>
                      <span style={mutedStyle}>온도 / 습도 / 수위 / 조도</span>
                    </div>
                    <div style={graphPlaceholderStyle}>
                      <strong>그래프 자리</strong>
                      <span style={mutedStyle}>
                        다음 단계에서 월별 꺾은선 그래프와 마우스 툴팁을 붙일게요.
                      </span>
                    </div>
                  </div>
                </div>
              )}
            </Panel>
          </section>
        )}

        {activeScreen === "chat" && (
          <Panel title="마리모와 대화하기" chip="대화">
            <div style={chatPreviewStyle}>
              {chatMessages.map((message) => (
                <div
                  key={message.id}
                  style={chatBubbleStyle(message.from === "marimo")}
                >
                  {message.text}
                </div>
              ))}
            </div>

            <div style={chatInputBarStyle}>
              <input
                type="text"
                defaultValue="메시지를 입력해 보세요"
                readOnly
                style={chatInputStyle}
                aria-label="메시지 입력"
              />
              <button type="button" style={sendButtonStyle}>
                전송
              </button>
            </div>
          </Panel>
        )}

        {activeScreen === "settings" && (
          <section style={gridTwoStyle}>
            <Panel title="초보자용 설정">
              <p style={leadStyle}>
                이미지 보관, 알림, 화면 구조처럼 자주 확인하는 부분을 먼저 보기 쉽게 정리해두는
                화면이에요.
              </p>
            </Panel>

            <Panel title="설정 항목" chip="정리 중">
              <div style={settingRowStyle}>알림 상태: ON</div>
              <div style={settingRowStyle}>이미지 보관: incoming 폴더</div>
            </Panel>
          </section>
        )}
      </main>
    </div>
  );
}

function Panel({ title, chip, children }) {
  return (
    <article style={panelStyle}>
      <div style={panelHeadStyle}>
        <h2 style={titleStyle}>{title}</h2>
        {chip ? <span style={chipStyle}>{chip}</span> : <span />}
      </div>
      {children}
    </article>
  );
}

const shellStyle = {
  minHeight: "100vh",
  color: "#17311c",
  background:
    "linear-gradient(to bottom, #d7f3ff 0%, #8fd3ff 58%, #76c56b 58%, #59ae55 100%)",
  backgroundAttachment: "fixed",
};

const headerStyle = {
  position: "sticky",
  top: 0,
  zIndex: 20,
  display: "flex",
  alignItems: "center",
  justifyContent: "space-between",
  gap: "16px",
  padding: "16px 20px",
  background: "linear-gradient(to bottom, rgba(17, 66, 31, 0.98), rgba(15, 57, 25, 0.96))",
  color: "#fff",
  boxShadow: "0 8px 20px rgba(0, 0, 0, 0.18)",
};

const brandStyle = {
  fontSize: "1.15rem",
  fontWeight: 800,
  letterSpacing: "0.08em",
};

const subtitleStyle = {
  marginTop: "4px",
  fontSize: "0.9rem",
  color: "rgba(255, 255, 255, 0.78)",
};

const navStyle = {
  display: "flex",
  gap: "10px",
  flexWrap: "wrap",
};

const navButtonStyle = (active) => ({
  border: "1px solid transparent",
  borderRadius: "999px",
  padding: "10px 16px",
  background: "transparent",
  color: active ? "#ffffff" : "rgba(255, 255, 255, 0.88)",
  cursor: "pointer",
  outline: active ? "1px solid rgba(255, 255, 255, 0.18)" : "none",
  boxShadow: "none",
});

const mainStyle = {
  width: "min(1280px, calc(100vw - 24px))",
  margin: "0 auto",
  padding: "18px 0 88px",
};

const gridThreeStyle = {
  display: "grid",
  gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))",
  gap: "18px",
};

const gridTwoStyle = {
  display: "grid",
  gridTemplateColumns: "repeat(auto-fit, minmax(320px, 1fr))",
  gap: "18px",
};

const screenStackStyle = {
  display: "grid",
  gap: "18px",
};

const sensorHeroGridStyle = {
  display: "grid",
  gridTemplateColumns: "repeat(auto-fit, minmax(320px, 1fr))",
  gap: "18px",
};

const panelStyle = {
  minHeight: "280px",
  border: "3px solid #7b5a2d",
  borderRadius: "26px",
  background: "linear-gradient(to bottom, #fff8e8, #fff4cf)",
  boxShadow: "0 18px 40px rgba(29, 44, 25, 0.18)",
  padding: "18px",
};

const panelHeadStyle = {
  display: "flex",
  justifyContent: "space-between",
  alignItems: "center",
  gap: "12px",
  marginBottom: "16px",
};

const titleStyle = {
  margin: 0,
  fontSize: "1.1rem",
};

const chipStyle = {
  display: "inline-flex",
  alignItems: "center",
  justifyContent: "center",
  borderRadius: "999px",
  border: "2px solid #7b5a2d",
  padding: "6px 10px",
  background: "#fff7d9",
  fontWeight: 700,
  fontSize: "0.78rem",
};

const leadStyle = {
  margin: "0 0 14px",
  color: "#5f6b62",
  lineHeight: 1.7,
};

const mutedStyle = {
  color: "#5f6b62",
  lineHeight: 1.55,
};

const listStyle = {
  margin: 0,
  paddingLeft: "18px",
  display: "grid",
  gap: "10px",
  lineHeight: 1.6,
};

const listItemStyle = {
  color: "#28342a",
};

const imageSlotStyle = {
  minHeight: "200px",
  borderRadius: "22px",
  border: "2px dashed rgba(47, 127, 48, 0.24)",
  background: "rgba(255, 248, 230, 0.78)",
  display: "grid",
  placeItems: "center",
  gap: "8px",
  textAlign: "center",
  padding: "20px",
};

const avatarSlotStyle = {
  minHeight: "200px",
  borderRadius: "22px",
  border: "2px dashed rgba(47, 127, 48, 0.24)",
  background: "rgba(255, 248, 230, 0.78)",
  display: "grid",
  placeItems: "center",
  gap: "8px",
  textAlign: "center",
  padding: "20px",
};

const imageStrongStyle = {
  fontSize: "1.08rem",
};

const questItemStyle = {
  padding: "14px 16px",
  borderRadius: "16px",
  background: "rgba(255, 255, 255, 0.58)",
  border: "1px solid rgba(123, 90, 45, 0.14)",
  marginBottom: "12px",
  display: "grid",
  gap: "4px",
};

const sensorGridStyle = {
  display: "grid",
  gridTemplateColumns: "repeat(2, minmax(0, 1fr))",
  gap: "12px",
};

const sensorCardStyle = {
  display: "grid",
  gap: "4px",
  padding: "14px",
  borderRadius: "16px",
  background: "rgba(255,255,255,0.72)",
  border: "1px solid rgba(123,90,45,0.16)",
};

const sensorValueStyle = {
  fontSize: "1.18rem",
};

const historyBoxStyle = {
  display: "grid",
  gap: "12px",
};

const historyRowStyle = {
  display: "grid",
  gridTemplateColumns: "88px 1fr",
  gap: "12px",
  padding: "12px 14px",
  borderRadius: "16px",
  background: "rgba(255,255,255,0.7)",
  border: "1px solid rgba(123,90,45,0.14)",
};

const modeSwitchStyle = {
  display: "inline-flex",
  gap: "10px",
  padding: "6px",
  borderRadius: "999px",
  background: "rgba(255,255,255,0.56)",
  marginBottom: "14px",
};

const modeButtonStyle = (active) => ({
  border: "none",
  borderRadius: "999px",
  padding: "10px 18px",
  background: active ? "linear-gradient(to bottom, #7bd469, #3d8d34)" : "transparent",
  color: active ? "#fff" : "#26362a",
  fontWeight: 700,
  cursor: "pointer",
});

const weeklyListStyle = {
  display: "grid",
  gap: "12px",
};

const weeklyCardStyle = {
  display: "grid",
  gap: "8px",
  padding: "14px 16px",
  borderRadius: "16px",
  background: "rgba(255,255,255,0.72)",
  border: "1px solid rgba(123,90,45,0.14)",
};

const weeklyTitleStyle = {
  color: "#2e8f2c",
};

const weeklyTextStyle = {
  lineHeight: 1.55,
};

const weeklyNoteStyle = {
  color: "#5f6b62",
  fontSize: "0.95rem",
};

const monthlyLayoutStyle = {
  display: "grid",
  gap: "14px",
};

const monthGridStyle = {
  display: "grid",
  gridTemplateColumns: "repeat(auto-fit, minmax(72px, 1fr))",
  gap: "10px",
};

const monthButtonStyle = (active) => ({
  border: "1px solid rgba(123, 90, 45, 0.16)",
  borderRadius: "14px",
  padding: "10px 12px",
  background: active ? "linear-gradient(to bottom, #7bd469, #3d8d34)" : "rgba(255,255,255,0.72)",
  color: active ? "#fff" : "#28342a",
  fontWeight: 700,
  cursor: "pointer",
});

const graphBoxStyle = {
  display: "grid",
  gap: "12px",
};

const graphHeaderStyle = {
  display: "flex",
  alignItems: "baseline",
  justifyContent: "space-between",
  gap: "12px",
};

const graphPlaceholderStyle = {
  minHeight: "220px",
  borderRadius: "18px",
  border: "1px dashed rgba(123,90,45,0.18)",
  background: "rgba(255,255,255,0.42)",
  display: "grid",
  placeItems: "center",
  color: "#5f6b62",
  textAlign: "center",
  padding: "18px",
};

const chatPreviewStyle = {
  display: "grid",
  gap: "12px",
  marginBottom: "18px",
};

const chatBubbleStyle = (isMarimo) => ({
  maxWidth: "78%",
  padding: "14px 15px",
  borderRadius: "18px",
  background: isMarimo
    ? "rgba(255,255,255,0.7)"
    : "linear-gradient(to bottom, #fff9cc, #ffe26d)",
  border: "1px solid rgba(123,90,45,0.14)",
});

const chatInputBarStyle = {
  display: "grid",
  gridTemplateColumns: "1fr auto",
  gap: "12px",
  padding: "12px",
  borderRadius: "18px",
  background: "rgba(255,255,255,0.62)",
  border: "1px solid rgba(123,90,45,0.14)",
};

const chatInputStyle = {
  border: "none",
  borderRadius: "14px",
  padding: "14px 16px",
  background: "#fff",
  color: "#33403a",
  fontSize: "1rem",
  outline: "none",
};

const sendButtonStyle = {
  border: "none",
  borderRadius: "14px",
  padding: "14px 20px",
  background: "linear-gradient(to bottom, #7bd469, #3d8d34)",
  color: "#fff",
  fontWeight: 700,
  cursor: "pointer",
};

const settingRowStyle = {
  padding: "14px 16px",
  border: "1px solid rgba(123,90,45,0.16)",
  borderRadius: "18px",
  background: "rgba(255,255,255,0.72)",
  marginBottom: "12px",
};
