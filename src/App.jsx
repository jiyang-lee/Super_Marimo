import React, { useEffect, useMemo, useState } from "react";

const screens = [
  { key: "home", label: "Home" },
  { key: "sensor", label: "Sensor" },
  { key: "chat", label: "Chat" },
  { key: "settings", label: "Settings" },
];

const homeNotices = [
  "지금은 화면이 실제로 보이는지 먼저 확인하는 단계예요.",
  "공지사항, 전체 마리모 이미지, 오늘의 퀘스트 구조를 다시 살렸어요.",
  "이미지는 아직 비워 두고, 나중에 넣기 쉽게 자리만 준비해 두었어요.",
];

const homeQuests = [
  { title: "물 상태 확인", description: "센서 값이 안정적인지 먼저 살펴봐요." },
  { title: "온도 상태 확인", description: "마리모가 지내기 좋은 온도인지 봐요." },
];

const hourlyHistory = [
  { time: "09:00", text: "온도 24°C · 습도 47% · 수위 81% · 조도 410 lux" },
  { time: "12:00", text: "온도 25°C · 습도 45% · 수위 80% · 조도 620 lux" },
  { time: "15:00", text: "온도 24°C · 습도 48% · 수위 79% · 조도 540 lux" },
  { time: "18:00", text: "온도 23°C · 습도 52% · 수위 80% · 조도 360 lux" },
  { time: "21:00", text: "온도 22°C · 습도 55% · 수위 81% · 조도 240 lux" },
];

const weeklyByMonth = {
  "1월": [
    { range: "01.01.~01.07.", text: "온도 : 24.0도, 습도 : 51%, 수위 : 82%, 조도 : 480lux" },
    { range: "01.08.~01.14.", text: "온도 : 23.8도, 습도 : 50%, 수위 : 81%, 조도 : 510lux" },
    { range: "01.15.~01.21.", text: "온도 : 24.2도, 습도 : 49%, 수위 : 83%, 조도 : 530lux" },
    { range: "01.22.~01.31.", text: "온도 : 24.5도, 습도 : 48%, 수위 : 84%, 조도 : 560lux" },
  ],
  "2월": [
    { range: "02.01.~02.07.", text: "온도 : 24.8도, 습도 : 50%, 수위 : 82%, 조도 : 600lux" },
    { range: "02.08.~02.14.", text: "온도 : 25.1도, 습도 : 52%, 수위 : 81%, 조도 : 640lux" },
    { range: "02.15.~02.21.", text: "온도 : 24.9도, 습도 : 49%, 수위 : 82%, 조도 : 620lux" },
    { range: "02.22.~02.29.", text: "온도 : 24.7도, 습도 : 48%, 수위 : 83%, 조도 : 610lux" },
  ],
  "3월": [
    { range: "03.01.~03.07.", text: "온도 : 24.4도, 습도 : 49%, 수위 : 82%, 조도 : 700lux" },
    { range: "03.08.~03.14.", text: "온도 : 24.6도, 습도 : 50%, 수위 : 82%, 조도 : 720lux" },
    { range: "03.15.~03.21.", text: "온도 : 24.8도, 습도 : 51%, 수위 : 83%, 조도 : 740lux" },
    { range: "03.22.~03.31.", text: "온도 : 25.0도, 습도 : 52%, 수위 : 84%, 조도 : 760lux" },
  ],
  "4월": [
    { range: "04.01.~04.07.", text: "온도 : 24.1도, 습도 : 50%, 수위 : 81%, 조도 : 820lux" },
    { range: "04.08.~04.14.", text: "온도 : 24.3도, 습도 : 51%, 수위 : 82%, 조도 : 860lux" },
    { range: "04.15.~04.21.", text: "온도 : 24.5도, 습도 : 50%, 수위 : 82%, 조도 : 900lux" },
    { range: "04.22.~04.30.", text: "온도 : 24.7도, 습도 : 51%, 수위 : 83%, 조도 : 940lux" },
  ],
  "5월": [
    { range: "05.01.~05.07.", text: "온도 : 24.9도, 습도 : 52%, 수위 : 82%, 조도 : 980lux" },
    { range: "05.08.~05.14.", text: "온도 : 25.1도, 습도 : 53%, 수위 : 83%, 조도 : 1,020lux" },
    { range: "05.15.~05.21.", text: "온도 : 25.3도, 습도 : 54%, 수위 : 83%, 조도 : 1,050lux" },
    { range: "05.22.~05.31.", text: "온도 : 25.5도, 습도 : 55%, 수위 : 84%, 조도 : 1,120lux" },
  ],
  "6월": [
    { range: "06.01.~06.07.", text: "온도 : 24.6도, 습도 : 51%, 수위 : 83%, 조도 : 1,140lux" },
    { range: "06.08.~06.14.", text: "온도 : 24.8도, 습도 : 52%, 수위 : 83%, 조도 : 1,180lux" },
    { range: "06.15.~06.21.", text: "온도 : 25.0도, 습도 : 53%, 수위 : 84%, 조도 : 1,220lux" },
    { range: "06.22.~06.30.", text: "온도 : 25.2도, 습도 : 54%, 수위 : 84%, 조도 : 1,260lux" },
  ],
};

const monthSeries = {
  "1월": [
    { day: 1, temp: 24, humidity: 48, water: 82, light: 1800 },
    { day: 5, temp: 24.2, humidity: 49, water: 83, light: 2200 },
    { day: 10, temp: 24.5, humidity: 50, water: 83, light: 2600 },
    { day: 15, temp: 24.8, humidity: 51, water: 84, light: 2800 },
    { day: 20, temp: 24.6, humidity: 50, water: 83, light: 3000 },
    { day: 25, temp: 24.3, humidity: 49, water: 82, light: 3400 },
    { day: 30, temp: 24.1, humidity: 48, water: 82, light: 3600 },
  ],
  "2월": [
    { day: 1, temp: 24.5, humidity: 50, water: 82, light: 2600 },
    { day: 5, temp: 24.7, humidity: 51, water: 82, light: 3000 },
    { day: 10, temp: 24.9, humidity: 52, water: 83, light: 3400 },
    { day: 15, temp: 25.0, humidity: 52, water: 83, light: 3800 },
    { day: 20, temp: 24.8, humidity: 51, water: 83, light: 4200 },
    { day: 25, temp: 24.6, humidity: 50, water: 82, light: 4600 },
    { day: 29, temp: 24.5, humidity: 49, water: 82, light: 5000 },
  ],
  "3월": [
    { day: 1, temp: 24.2, humidity: 49, water: 82, light: 3200 },
    { day: 5, temp: 24.4, humidity: 50, water: 82, light: 3600 },
    { day: 10, temp: 24.6, humidity: 50, water: 83, light: 4100 },
    { day: 15, temp: 24.8, humidity: 51, water: 83, light: 4500 },
    { day: 20, temp: 24.9, humidity: 52, water: 84, light: 4900 },
    { day: 25, temp: 25.0, humidity: 52, water: 84, light: 5200 },
    { day: 31, temp: 24.8, humidity: 51, water: 83, light: 5600 },
  ],
  "4월": [
    { day: 1, temp: 24.0, humidity: 50, water: 81, light: 4200 },
    { day: 5, temp: 24.2, humidity: 51, water: 82, light: 4700 },
    { day: 10, temp: 24.4, humidity: 51, water: 82, light: 5200 },
    { day: 15, temp: 24.5, humidity: 52, water: 83, light: 5800 },
    { day: 20, temp: 24.6, humidity: 52, water: 83, light: 6200 },
    { day: 25, temp: 24.8, humidity: 51, water: 84, light: 6800 },
    { day: 30, temp: 24.9, humidity: 50, water: 84, light: 7200 },
  ],
  "5월": [
    { day: 1, temp: 24.8, humidity: 52, water: 82, light: 4800 },
    { day: 5, temp: 25.0, humidity: 53, water: 83, light: 5200 },
    { day: 10, temp: 25.2, humidity: 54, water: 83, light: 5800 },
    { day: 15, temp: 25.4, humidity: 54, water: 84, light: 6400 },
    { day: 20, temp: 25.3, humidity: 55, water: 84, light: 7000 },
    { day: 25, temp: 25.1, humidity: 54, water: 84, light: 7600 },
    { day: 30, temp: 25.0, humidity: 53, water: 83, light: 7800 },
  ],
  "6월": [
    { day: 1, temp: 24.6, humidity: 51, water: 83, light: 5200 },
    { day: 5, temp: 24.8, humidity: 52, water: 83, light: 5800 },
    { day: 10, temp: 25.0, humidity: 53, water: 84, light: 6200 },
    { day: 15, temp: 25.2, humidity: 54, water: 84, light: 6800 },
    { day: 20, temp: 25.3, humidity: 54, water: 84, light: 7200 },
    { day: 25, temp: 25.1, humidity: 53, water: 83, light: 7600 },
    { day: 30, temp: 25.0, humidity: 52, water: 83, light: 8000 },
  ],
};

const chartSeries = monthSeries["5월"];

const chatMessages = [
  { id: 1, from: "marimo", text: "안녕! 오늘 센서 상태를 함께 볼까?" },
  { id: 2, from: "user", text: "좋아, 위클릭이랑 머슬릭도 확인해볼게." },
  { id: 3, from: "marimo", text: "좋아. 화면이 잘 보이면 이제 세부 조정만 남았어." },
];

export default function App() {
  const [activeScreen, setActiveScreen] = useState("home");
  const [sensorMode, setSensorMode] = useState("weekly");
  const [activeMonth, setActiveMonth] = useState("5월");
  const [hoverPoint, setHoverPoint] = useState(null);

  useEffect(() => {
    document.getElementById("fallback-root")?.remove();
  }, []);

  const monthlyData = monthSeries[activeMonth] ?? chartSeries;

  const chartMetrics = useMemo(() => {
    const width = 100;
    const height = 240;
    const padding = 28;
    const plotWidth = width - padding * 2;
    const plotHeight = height - padding * 2;
    const tempMax = 30;
    const tempMin = 20;
    const lightMax = 10000;

    const scaleX = (index, length) =>
      padding + (length <= 1 ? 0 : (plotWidth * index) / (length - 1));
    const scaleY = (value, min, max) =>
      padding + plotHeight - ((value - min) / (max - min)) * plotHeight;

    const buildLine = (key, min, max) =>
      monthlyData
        .map((point, index) => `${scaleX(index, monthlyData.length)},${scaleY(point[key], min, max)}`)
        .join(" ");

    return {
      width,
      height,
      padding,
      scaleX,
      scaleY,
      tempLine: buildLine("temp", tempMin, tempMax),
      humidityLine: buildLine("humidity", 0, 100),
      waterLine: buildLine("water", 0, 100),
      lightLine: buildLine("light", 0, lightMax),
      tempMin,
      tempMax,
      lightMax,
    };
  }, [monthlyData]);

  return (
    <div style={shellStyle}>
      <header style={headerStyle}>
        <div>
          <div style={brandStyle}>MARIMO QUEST</div>
          <div style={subtitleStyle}>화면을 확인하고 다시 정리하는 기준 화면</div>
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
              <p style={leadStyle}>{homeNotices[0]}</p>
              <ul style={listStyle}>
                <li style={listItemStyle}>{homeNotices[1]}</li>
                <li style={listItemStyle}>{homeNotices[2]}</li>
              </ul>
            </Panel>

            <Panel title="전체 마리모 이미지">
              <div style={imageSlotStyle}>
                <strong style={imageStrongStyle}>이미지 자리</strong>
                <span style={mutedStyle}>나중에 마리모 전체 이미지를 넣을 위치예요.</span>
              </div>
            </Panel>

            <Panel title="오늘의 퀘스트" chip="DAY 01">
              {homeQuests.map((quest) => (
                <div key={quest.title} style={questItemStyle}>
                  <strong>{quest.title}</strong>
                  <span style={mutedStyle}>{quest.description}</span>
                </div>
              ))}
            </Panel>
          </section>
        )}

        {activeScreen === "sensor" && (
          <section style={screenStackStyle}>
            <div style={sensorHeroGridStyle}>
              <Panel title="마리모 이미지" chip="캐릭터">
                <div style={avatarSlotStyle}>
                  <strong style={imageStrongStyle}>전체 마리모 이미지</strong>
                  <span style={mutedStyle}>왼쪽에는 나중에 전체 마리모 캐릭터 이미지를 넣을 수 있어요.</span>
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
                <p style={leadStyle}>현재 값은 예시예요. 실제 센서가 연결되면 이 숫자만 자동으로 바뀌게 됩니다.</p>
              </Panel>
            </div>

            <Panel title="시간별 센서 이력" chip="기록">
              <div style={historyBoxStyle}>
                {hourlyHistory.map((item) => (
                  <div key={item.time} style={historyRowStyle}>
                    <strong>{item.time}</strong>
                    <span style={mutedStyle}>{item.text}</span>
                  </div>
                ))}
              </div>
            </Panel>

            <Panel title="위클릭 / 머슬릭 자료" chip="주간 / 월간">
              <div style={modeSwitchStyle}>
                <button
                  type="button"
                  onClick={() => setSensorMode("weekly")}
                  style={modeButtonStyle(sensorMode === "weekly")}
                >
                  위클릭
                </button>
                <button
                  type="button"
                  onClick={() => setSensorMode("monthly")}
                  style={modeButtonStyle(sensorMode === "monthly")}
                >
                  머슬릭
                </button>
              </div>

              {sensorMode === "weekly" ? (
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
                    {Object.keys(monthSeries).map((month) => (
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

                    <div style={graphSvgWrapStyle}>
                      <svg
                        viewBox={`0 0 ${chartMetrics.width} ${chartMetrics.height}`}
                        style={svgStyle}
                        onMouseLeave={() => setHoverPoint(null)}
                        onMouseMove={(event) => {
                          const rect = event.currentTarget.getBoundingClientRect();
                          const x = ((event.clientX - rect.left) / rect.width) * chartMetrics.width;
                          const nearestIndex = monthlyData.reduce(
                            (best, point, index) => {
                              const pointX = chartMetrics.scaleX(index, monthlyData.length);
                              const distance = Math.abs(pointX - x);
                              return distance < best.distance
                                ? { index, distance, pointX }
                                : best;
                            },
                            { index: 0, distance: Number.POSITIVE_INFINITY, pointX: 0 },
                          );
                          setHoverPoint(nearestIndex);
                        }}
                      >
                        {[0, 25, 50, 75, 100].map((tick) => {
                          const y = chartMetrics.scaleY(tick, 0, 100);
                          return (
                            <g key={`temp-${tick}`}>
                              <line x1="28" x2="72" y1={y} y2={y} stroke="#ffffff" strokeOpacity="0.2" />
                              <text x="10" y={y + 4} fontSize="4" fill="#846a2a">
                                {tick}
                              </text>
                            </g>
                          );
                        })}

                        {[0, 2500, 5000, 7500, 10000].map((tick) => {
                          const y = chartMetrics.scaleY(tick, 0, chartMetrics.lightMax);
                          return (
                            <text key={`light-${tick}`} x="75" y={y + 4} fontSize="4" fill="#da8f00">
                              {tick}
                            </text>
                          );
                        })}

                        <polyline fill="none" stroke="#ff8f4d" strokeWidth="1.8" points={chartMetrics.tempLine} />
                        <polyline fill="none" stroke="#4f9cff" strokeWidth="1.8" points={chartMetrics.humidityLine} />
                        <polyline fill="none" stroke="#55b95b" strokeWidth="1.8" points={chartMetrics.waterLine} />
                        <polyline fill="none" stroke="#d4a012" strokeWidth="1.8" points={chartMetrics.lightLine} />

                        {hoverPoint && monthlyData[hoverPoint.index] ? (
                          <>
                            <line
                              x1={hoverPoint.pointX}
                              x2={hoverPoint.pointX}
                              y1="28"
                              y2="212"
                              stroke="#2d4f6b"
                              strokeWidth="0.8"
                              strokeDasharray="2 2"
                            />
                            <circle
                              cx={hoverPoint.pointX}
                              cy={chartMetrics.scaleY(monthlyData[hoverPoint.index].temp, 20, 30)}
                              r="1.8"
                              fill="#ff8f4d"
                            />
                            <circle
                              cx={hoverPoint.pointX}
                              cy={chartMetrics.scaleY(monthlyData[hoverPoint.index].humidity, 0, 100)}
                              r="1.8"
                              fill="#4f9cff"
                            />
                            <circle
                              cx={hoverPoint.pointX}
                              cy={chartMetrics.scaleY(monthlyData[hoverPoint.index].water, 0, 100)}
                              r="1.8"
                              fill="#55b95b"
                            />
                            <circle
                              cx={hoverPoint.pointX}
                              cy={chartMetrics.scaleY(monthlyData[hoverPoint.index].light, 0, chartMetrics.lightMax)}
                              r="1.8"
                              fill="#d4a012"
                            />
                          </>
                        ) : null}
                      </svg>

                      <div style={legendStyle}>
                        <span><i style={{ ...legendDotStyle, background: "#ff8f4d" }} />온도</span>
                        <span><i style={{ ...legendDotStyle, background: "#4f9cff" }} />습도</span>
                        <span><i style={{ ...legendDotStyle, background: "#55b95b" }} />수위</span>
                        <span><i style={{ ...legendDotStyle, background: "#d4a012" }} />조도</span>
                      </div>

                      <div style={tooltipStyle}>
                        {hoverPoint && monthlyData[hoverPoint.index] ? (
                          <>
                            <strong>
                              {activeMonth} / {monthlyData[hoverPoint.index].day}일
                            </strong>
                            <span style={tooltipLineStyle}>온도 {monthlyData[hoverPoint.index].temp}°C</span>
                            <span style={tooltipLineStyle}>습도 {monthlyData[hoverPoint.index].humidity}%</span>
                            <span style={tooltipLineStyle}>수위 {monthlyData[hoverPoint.index].water}%</span>
                            <span style={tooltipLineStyle}>조도 {monthlyData[hoverPoint.index].light.toLocaleString()} lux</span>
                          </>
                        ) : (
                          <span style={mutedStyle}>그래프 선 위에 마우스를 올리면 해당 날짜의 값을 볼 수 있어요.</span>
                        )}
                      </div>
                    </div>
                  </div>
                </div>
              )}
            </Panel>
          </section>
        )}

        {activeScreen === "chat" && (
          <Panel title="마리모와 대화하기" chip="채팅">
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
                readOnly
                defaultValue="메시지를 입력해 보세요"
                aria-label="메시지 입력"
                style={chatInputStyle}
              />
              <button type="button" style={sendButtonStyle}>
                전송
              </button>
            </div>
          </Panel>
        )}

        {activeScreen === "settings" && (
          <section style={gridTwoStyle}>
            <Panel title="초보자용 설정" chip="안내">
              <div style={settingRowStyle}>이미지 보관: incoming 폴더에 먼저 넣고 나중에 분리하면 돼요.</div>
              <div style={settingRowStyle}>화면 기준: Home, Sensor, Chat, Settings 순으로 하나씩 다듬으면 돼요.</div>
            </Panel>

            <Panel title="작업 메모" chip="체크">
              <div style={settingRowStyle}>브랜치: frontend/jeong에서 작업을 이어가면 돼요.</div>
              <div style={settingRowStyle}>커밋: 큰 수정 후에는 체크포인트를 남기면 안전해요.</div>
            </Panel>
          </section>
        )}
      </main>
    </div>
  );
}

function Panel({ title, chip, children }) {
  return (
    <section style={panelStyle}>
      <div style={panelHeadStyle}>
        <strong style={panelTitleStyle}>{title}</strong>
        {chip ? <span style={chipStyle}>{chip}</span> : <span />}
      </div>
      <div>{children}</div>
    </section>
  );
}

function chatBubbleStyle(isMarimo) {
  return {
    alignSelf: isMarimo ? "start" : "end",
    justifySelf: isMarimo ? "start" : "end",
    maxWidth: "78%",
    padding: "14px 15px",
    borderRadius: isMarimo ? "18px 18px 18px 4px" : "18px 18px 4px 18px",
    background: isMarimo
      ? "rgba(255,255,255,0.7)"
      : "linear-gradient(to bottom, #fff9cc, #ffe26d)",
    border: "1px solid rgba(123,90,45,0.14)",
  };
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

const panelTitleStyle = {
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

const graphSvgWrapStyle = {
  display: "grid",
  gap: "10px",
};

const svgStyle = {
  width: "100%",
  height: "260px",
  display: "block",
  background: "linear-gradient(180deg, rgba(234, 247, 255, 0.95) 0%, rgba(255,255,255,0.82) 100%)",
  borderRadius: "16px",
};

const legendStyle = {
  display: "flex",
  flexWrap: "wrap",
  gap: "14px",
  fontSize: "14px",
  alignItems: "center",
};

const legendDotStyle = {
  display: "inline-block",
  width: "10px",
  height: "10px",
  borderRadius: "999px",
  marginRight: "6px",
  verticalAlign: "middle",
};

const tooltipStyle = {
  display: "grid",
  gap: "4px",
  background: "#fff7e3",
  border: "1px solid #e4cb8a",
  borderRadius: "14px",
  padding: "12px 14px",
  minHeight: "92px",
};

const tooltipLineStyle = {
  color: "#43321a",
};

const chatPreviewStyle = {
  display: "grid",
  gap: "10px",
  marginBottom: "14px",
};

const chatInputBarStyle = {
  display: "flex",
  gap: "10px",
  alignItems: "center",
};

const chatInputStyle = {
  flex: 1,
  borderRadius: "14px",
  border: "1px solid #d8c4a1",
  padding: "12px 14px",
  fontSize: "16px",
};

const sendButtonStyle = {
  borderRadius: "14px",
  border: "1px solid #8d5a24",
  background: "linear-gradient(180deg, #ffe089 0%, #f2b73e 100%)",
  padding: "12px 18px",
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
