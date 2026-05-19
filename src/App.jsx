import React, { useEffect, useMemo, useState } from "react";

const screens = [
  { key: "home", label: "홈" },
  { key: "sensor", label: "센서" },
  { key: "chat", label: "채팅" },
  { key: "settings", label: "설정" },
];

const monthLabels = Array.from({ length: 12 }, (_, index) => `${index + 1}월`);

const guideItems = [
  { icon: "💧", title: "깨끗한 물", text: "항상 맑고 깨끗한 물을 유지해 주세요." },
  { icon: "☀️", title: "직사광선 X", text: "강한 직사광선은 피하고 부드러운 빛으로 두세요." },
  { icon: "🔄", title: "가끔 굴러주기", text: "마리모가 고르게 자라도록 가끔 굴려 주세요." },
  { icon: "💚", title: "사랑 주기", text: "자주 보고 말 걸어 주면 더 정성스럽게 느껴져요." },
];

const sensorRangeItems = [
  { label: "온도", key: "temperature", max: 100 },
  { label: "습도", key: "humidity", max: 100 },
  { label: "수위", key: "water", max: 100 },
  { label: "조도", key: "light", max: 10000 },
];

function makeWeeklySummaries(monthIndex) {
  const month = monthIndex + 1;
  const baseTemp = 23.8 + monthIndex * 0.12;
  const baseHumidity = 47 + monthIndex * 0.4;
  const baseWater = 79 + monthIndex * 0.25;
  const baseLight = 420 + monthIndex * 85;

  return [
    `${String(month).padStart(2, "0")}.01.~${String(month).padStart(2, "0")}.07. 온도 : ${(baseTemp + 0.1).toFixed(1)}도, 습도 : ${Math.round(baseHumidity)}%, 수위 : ${Math.round(baseWater)}%, 조도 : ${Math.round(baseLight)}lux`,
    `${String(month).padStart(2, "0")}.08.~${String(month).padStart(2, "0")}.14. 온도 : ${(baseTemp + 0.4).toFixed(1)}도, 습도 : ${Math.round(baseHumidity + 1)}%, 수위 : ${Math.round(baseWater + 1)}%, 조도 : ${Math.round(baseLight + 140)}lux`,
    `${String(month).padStart(2, "0")}.15.~${String(month).padStart(2, "0")}.21. 온도 : ${(baseTemp + 0.7).toFixed(1)}도, 습도 : ${Math.round(baseHumidity + 2)}%, 수위 : ${Math.round(baseWater + 1)}%, 조도 : ${Math.round(baseLight + 240)}lux`,
    `${String(month).padStart(2, "0")}.22.~${String(month).padStart(2, "0")}.31. 온도 : ${(baseTemp + 0.9).toFixed(1)}도, 습도 : ${Math.round(baseHumidity + 3)}%, 수위 : ${Math.round(baseWater + 2)}%, 조도 : ${Math.round(baseLight + 360)}lux`,
  ];
}

function makeMonthlySeries(monthIndex) {
  const month = monthIndex + 1;
  const daysInMonth = new Date(2026, month, 0).getDate();
  const rawDays = [1, 5, 10, 15, 20, 25, 30].filter((day) => day <= daysInMonth);

  return rawDays.map((day, index) => {
    const wobble = Math.sin((monthIndex + index + 1) * 0.8) * 0.45;
    return {
      day,
      temp: +(24.1 + monthIndex * 0.06 + wobble * 0.8).toFixed(1),
      humidity: Math.round(46 + monthIndex * 0.5 + index * 1.8 + wobble * 2),
      water: Math.round(78 + monthIndex * 0.35 + index * 1.4 + wobble * 1.4),
      light: Math.round(900 + monthIndex * 420 + index * 720 + Math.max(0, wobble * 220)),
    };
  });
}

function makeClock() {
  return new Intl.DateTimeFormat("ko-KR", {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false,
  }).format(new Date());
}

function makeChart(monthIndex) {
  const series = makeMonthlySeries(monthIndex);
  const width = 100;
  const height = 190;
  const leftAxis = 8;
  const rightAxis = 92;
  const top = 14;
  const bottom = 18;
  const plotWidth = rightAxis - leftAxis;
  const plotHeight = height - top - bottom;
  const count = series.length || 1;
  const scaleX = (index) => leftAxis + (count === 1 ? plotWidth / 2 : (plotWidth * index) / (count - 1));
  const scaleY = (value, min, max) => top + plotHeight - ((value - min) / (max - min)) * plotHeight;

  const path = (getter, min, max) =>
    series.map((point, index) => `${scaleX(index)},${scaleY(getter(point), min, max)}`).join(" ");

  return {
    series,
    width,
    height,
    top,
    bottom,
    scaleX,
    scaleY,
    tempPath: path((point) => point.temp, 0, 100),
    humidityPath: path((point) => point.humidity, 0, 100),
    waterPath: path((point) => point.water, 0, 100),
    lightPath: path((point) => point.light, 0, 10000),
  };
}

function Panel({ title, chip, children }) {
  return (
    <section className="panel">
      <div className="panel-head">
        <strong>{title}</strong>
        {chip ? <span className="chip">{chip}</span> : <span />}
      </div>
      <div className="panel-body">{children}</div>
    </section>
  );
}

export default function App() {
  const [activeScreen, setActiveScreen] = useState("home");
  const [sensorMode, setSensorMode] = useState("weekly");
  const [selectedWeekMonth, setSelectedWeekMonth] = useState(4);
  const [selectedChartMonth, setSelectedChartMonth] = useState(4);
  const [notificationEnabled, setNotificationEnabled] = useState(true);
  const [chatMode, setChatMode] = useState("텍스트");
  const [chatDraft, setChatDraft] = useState("");
  const [openModal, setOpenModal] = useState(null);
  const [clockText, setClockText] = useState(makeClock());
  const [hoverPoint, setHoverPoint] = useState(null);
  const [sensorRanges, setSensorRanges] = useState({
    temperatureMin: 0,
    temperatureMax: 100,
    humidityMin: 0,
    humidityMax: 100,
    waterMin: 0,
    waterMax: 100,
    lightMin: 0,
    lightMax: 10000,
  });

  useEffect(() => {
    const timer = setInterval(() => setClockText(makeClock()), 1000);
    return () => clearInterval(timer);
  }, []);

  const weeklySummaries = useMemo(() => makeWeeklySummaries(selectedWeekMonth), [selectedWeekMonth]);
  const chart = useMemo(() => makeChart(selectedChartMonth), [selectedChartMonth]);
  const currentPoint = hoverPoint ? chart.series[hoverPoint.index] : null;

  function handleChartMove(event) {
    const rect = event.currentTarget.getBoundingClientRect();
    const pointerX = ((event.clientX - rect.left) / rect.width) * chart.width;
    const pointerY = ((event.clientY - rect.top) / rect.height) * chart.height;

    const closest = chart.series.reduce(
      (best, point, index) => {
        const x = chart.scaleX(index);
        const distance = Math.abs(pointerX - x);
        return distance < best.distance ? { index, distance, x } : best;
      },
      { index: 0, distance: Number.POSITIVE_INFINITY, x: chart.scaleX(0) },
    );

    setHoverPoint({
      index: closest.index,
      x: pointerX,
      y: Math.max(chart.top, Math.min(chart.height - 18, pointerY)),
    });
  }

  const homeNotices = [
    "지금은 화면이 실제로 보이는지 먼저 확인하는 단계예요.",
    "네비게이션은 가운데로 고정하고, 오른쪽 위에는 실시간 시간을 띄워둘게요.",
    "기능은 빼고 UI만 단순하게 정리해서 초보자도 보기 쉽게 만들었어요.",
  ];

  const homeQuests = [
    { title: "전체 구조 확인", description: "홈, 센서, 채팅, 설정이 한 화면 안에서 잘 나뉘는지 봐요." },
    { title: "이미지 자리 준비", description: "마리모 캐릭터와 아이콘은 나중에 바로 넣을 수 있게 비워둬요." },
  ];

  function closeModal() {
    setOpenModal(null);
  }

  return (
    <div className="app-shell">
      <header className="app-header">
        <div className="header-brand">
          <strong className="brand-name">MARIMO QUEST</strong>
          <span className="brand-subtitle">화면만 먼저 보이도록 단순하게 정리한 앱사이트</span>
        </div>

        <nav className="top-nav" aria-label="주요 화면 이동">
          {screens.map((screen) => (
            <button
              key={screen.key}
              type="button"
              className={`nav-button ${activeScreen === screen.key ? "is-active" : ""}`}
              onClick={() => {
                setActiveScreen(screen.key);
                setOpenModal(null);
                setHoverPoint(null);
              }}
            >
              {screen.label}
            </button>
          ))}
        </nav>

        <div className="clock-chip" aria-label="실시간 시간">
          {clockText}
        </div>
      </header>

      <main className="app-main">
        {activeScreen === "home" && (
          <section className="home-grid">
            <Panel title="공지사항" chip="초보자용">
              <p className="panel-lead">{homeNotices[0]}</p>
              <ul className="note-list">
                <li>{homeNotices[1]}</li>
                <li>{homeNotices[2]}</li>
              </ul>
            </Panel>

            <Panel title="전체 마리모 이미지" chip="이미지 자리">
              <div className="image-placeholder">
                <strong>이미지 자리</strong>
                <span>나중에 전체 마리모 이미지를 넣을 위치예요.</span>
              </div>
            </Panel>

            <Panel title="오늘의 퀘스트" chip="DAY 01">
              <div className="quest-list">
                {homeQuests.map((quest) => (
                  <div key={quest.title} className="quest-item">
                    <strong>{quest.title}</strong>
                    <span>{quest.description}</span>
                  </div>
                ))}
              </div>
            </Panel>
          </section>
        )}

        {activeScreen === "sensor" && (
          <section className="sensor-stack">
            <div className="sensor-top-grid">
              <Panel title="마리모 이미지" chip="캐릭터">
                <div className="image-placeholder tall">
                  <strong>전체 마리모 이미지</strong>
                  <span>왼쪽에는 나중에 캐릭터 이미지를 배치할 수 있어요.</span>
                </div>
              </Panel>

              <Panel title="현재 센서 상태" chip="실시간">
                <div className="metric-grid">
                  {[
                    ["온도", "24.0도"],
                    ["습도", "45%"],
                    ["수위", "80%"],
                    ["조도", "500 lux"],
                  ].map(([label, value]) => (
                    <div key={label} className="metric-card">
                      <span>{label}</span>
                      <strong>{value}</strong>
                    </div>
                  ))}
                </div>
                <p className="panel-lead">현재 값은 예시예요. 실제 센서가 연결되면 이 카드만 바뀌게 만들 수 있어요.</p>
              </Panel>
            </div>

            <Panel title="시간별 센서 이력" chip="기록">
              <div className="history-list scrollable-history">
                {Array.from({ length: 18 }, (_, index) => {
                  const hour = String(6 + index).padStart(2, "0");
                  const temperature = 23 + (index % 4);
                  const humidity = 45 + (index % 8);
                  const water = 79 + (index % 5);
                  const light = 240 + index * 60;
                  return (
                    <div key={hour} className="history-row">
                      <strong>{hour}:00</strong>
                      <span>
                        온도 {temperature}°C · 습도 {humidity}% · 수위 {water}% · 조도 {light} lux
                      </span>
                    </div>
                  );
                })}
              </div>
            </Panel>

            <Panel title="위클릭 / 머슬릭 자료" chip="주간 / 월간">
              <div className="mode-switch">
                <button
                  type="button"
                  className={`mode-button ${sensorMode === "weekly" ? "is-active" : ""}`}
                  onClick={() => {
                    setSensorMode("weekly");
                    setHoverPoint(null);
                  }}
                >
                  위클릭
                </button>
                <button
                  type="button"
                  className={`mode-button ${sensorMode === "monthly" ? "is-active" : ""}`}
                  onClick={() => {
                    setSensorMode("monthly");
                    setHoverPoint(null);
                  }}
                >
                  머슬릭
                </button>
              </div>

              <div className="month-grid">
                {monthLabels.map((month, index) => (
                  <button
                    key={month}
                    type="button"
                    className={`month-button ${index === (sensorMode === "weekly" ? selectedWeekMonth : selectedChartMonth) ? "is-active" : ""}`}
                    onClick={() => {
                      if (sensorMode === "weekly") {
                        setSelectedWeekMonth(index);
                      } else {
                        setSelectedChartMonth(index);
                        setHoverPoint(null);
                      }
                    }}
                  >
                    {month}
                  </button>
                ))}
              </div>

              <div className="sensor-switch-panel">
                {sensorMode === "weekly" ? (
                  <div className="weekly-list">
                    {weeklySummaries.map((text) => {
                      const [range, ...rest] = text.split(" ");
                      return (
                        <article key={range} className="weekly-card">
                          <strong className="weekly-range">{range}</strong>
                          <span className="weekly-text">{rest.join(" ")}</span>
                        </article>
                      );
                    })}
                  </div>
                ) : (
                  <div className="chart-card">
                    <div className="chart-header">
                      <strong>{monthLabels[selectedChartMonth]} 머슬릭 그래프</strong>
                      <span>온도 / 습도 / 수위 / 조도</span>
                    </div>

                    <div className="chart-panel">
                      <div className="chart-axis axis-left">
                        {[10000, 7500, 5000, 2500, 0].map((tick) => (
                          <span key={tick} style={{ top: `${chart.scaleY(tick, 0, 10000)}px` }}>
                            {tick}
                          </span>
                        ))}
                      </div>

                      <div
                        className="chart-viewport"
                        id="chartViewport"
                        onMouseLeave={() => setHoverPoint(null)}
                        onMouseMove={handleChartMove}
                      >
                        <svg className="chart-svg" viewBox={`0 0 ${chart.width} ${chart.height}`} preserveAspectRatio="none">
                          {[0, 25, 50, 75, 100].map((tick) => {
                            const y = chart.scaleY(tick, 0, 100);
                            return <line key={tick} x1="8" x2="92" y1={y} y2={y} className="chart-grid" />;
                          })}
                          <polyline className="line temp-line" points={chart.tempPath} />
                          <polyline className="line humidity-line" points={chart.humidityPath} />
                          <polyline className="line water-line" points={chart.waterPath} />
                          <polyline className="line light-line" points={chart.lightPath} />

                          {currentPoint ? (
                            <line
                              x1={hoverPoint.x}
                              x2={hoverPoint.x}
                              y1={chart.top}
                              y2={chart.height - chart.bottom}
                              className="chart-crosshair"
                            />
                          ) : null}
                        </svg>

                        <div className="chart-legend">
                          <span><i className="dot temp-dot" />온도</span>
                          <span><i className="dot humidity-dot" />습도</span>
                          <span><i className="dot water-dot" />수위</span>
                          <span><i className="dot light-dot" />조도</span>
                        </div>

                        {currentPoint ? (
                          <div
                            className="chart-tooltip"
                            style={{
                              left: `${Math.min(hoverPoint.x + 12, 66)}%`,
                              top: `${Math.min(hoverPoint.y - 48, 120)}px`,
                            }}
                          >
                            <strong>
                              {monthLabels[selectedChartMonth]} / {currentPoint.day}일
                            </strong>
                            <span>온도 {currentPoint.temp}°C</span>
                            <span>습도 {currentPoint.humidity}%</span>
                            <span>수위 {currentPoint.water}%</span>
                            <span>조도 {currentPoint.light.toLocaleString()} lux</span>
                          </div>
                        ) : null}
                      </div>

                      <div className="chart-axis axis-right">
                        {[0, 25, 50, 75, 100].map((tick) => (
                          <span key={`right-${tick}`} style={{ top: `${chart.scaleY(tick, 0, 100)}px` }}>
                            {tick}
                          </span>
                        ))}
                      </div>
                    </div>
                  </div>
                )}
              </div>
            </Panel>
          </section>
        )}

        {activeScreen === "chat" && (
          <section className="chat-card">
            <Panel title="마리모와 대화하기" chip="채팅">
              <div className="chat-list">
                {[
                  { id: 1, from: "marimo", text: "안녕! 오늘은 어떤 걸 확인해 볼까?" },
                  { id: 2, from: "user", text: "화면 구조부터 천천히 보고 싶어." },
                  { id: 3, from: "marimo", text: "좋아. 텍스트나 음성 모드를 바꿔도 입력 내용은 그대로 남겨둘게." },
                ].map((message) => (
                  <div key={message.id} className={`chat-row ${message.from}`}>
                    {message.from === "marimo" ? <span className="chat-avatar">M</span> : null}
                    <div className={`chat-bubble ${message.from}`}>{message.text}</div>
                  </div>
                ))}
              </div>

              <div className="chat-bar">
                <input
                  className="chat-input"
                  type="text"
                  value={chatDraft}
                  onChange={(event) => setChatDraft(event.target.value)}
                  placeholder="메시지를 입력해 주세요"
                />
                <button type="button" className="send-button">
                  전송
                </button>
                <button
                  type="button"
                  className={`mode-button ${chatMode === "음성" ? "is-active" : ""}`}
                  onClick={() => setChatMode((current) => (current === "음성" ? "텍스트" : "음성"))}
                >
                  음성
                </button>
              </div>
            </Panel>
          </section>
        )}

        {activeScreen === "settings" && (
          <section className="settings-grid">
            <Panel title="상태" chip="ON / OFF">
              <button
                type="button"
                className={`notification-toggle ${notificationEnabled ? "is-on" : "is-off"}`}
                onClick={() => setNotificationEnabled((current) => !current)}
              >
                {notificationEnabled ? "on" : "off"}
              </button>
            </Panel>

            <Panel title="센서" chip="범위 설정">
              <button
                type="button"
                className="setting-open-button"
                onClick={() => setOpenModal("sensor")}
              >
                온도 / 습도 / 수위 / 조도 범위 보기
              </button>
            </Panel>

            <Panel title="가이드" chip="안내">
              <button
                type="button"
                className="setting-open-button"
                onClick={() => setOpenModal("guide")}
              >
                관리 가이드 열기
              </button>
            </Panel>
          </section>
        )}
      </main>

      {openModal ? (
        <div className="modal-backdrop" onClick={(event) => event.target === event.currentTarget && closeModal()}>
          <div className="modal-card" role="dialog" aria-modal="true">
            <div className="modal-head">
              <strong>{openModal === "sensor" ? "센서 범위" : "가이드"}</strong>
              <button type="button" className="modal-close" onClick={closeModal}>
                닫기
              </button>
            </div>

            {openModal === "sensor" ? (
              <div className="range-grid">
                {sensorRangeItems.map((item) => {
                  const minKey = `${item.key}Min`;
                  const maxKey = `${item.key}Max`;
                  const minValue = sensorRanges[minKey];
                  const maxValue = sensorRanges[maxKey];

                  return (
                    <div key={item.key} className="range-row">
                      <strong>{item.label}</strong>
                      <div className="range-slider">
                        <div className="range-track">
                          <div
                            className="range-fill"
                            style={{
                              left: `${(minValue / item.max) * 100}%`,
                              width: `${((maxValue - minValue) / item.max) * 100}%`,
                            }}
                          />
                          <span
                            className="range-thumb left"
                            style={{ left: `${(minValue / item.max) * 100}%` }}
                          />
                          <span
                            className="range-thumb right"
                            style={{ left: `${(maxValue / item.max) * 100}%` }}
                          />
                        </div>
                        <div className="range-inputs">
                          <input
                            type="range"
                            min="0"
                            max={item.max}
                            value={minValue}
                            onChange={(event) => {
                              const nextValue = Math.min(Number(event.target.value), sensorRanges[maxKey]);
                              setSensorRanges((current) => ({ ...current, [minKey]: nextValue }));
                            }}
                          />
                          <input
                            type="range"
                            min="0"
                            max={item.max}
                            value={maxValue}
                            onChange={(event) => {
                              const nextValue = Math.max(Number(event.target.value), sensorRanges[minKey]);
                              setSensorRanges((current) => ({ ...current, [maxKey]: nextValue }));
                            }}
                          />
                        </div>
                        <div className="range-values">
                          <span>{minValue}</span>
                          <span>{maxValue}</span>
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            ) : (
              <div className="guide-grid">
                {guideItems.map((item) => (
                  <article key={item.title} className="guide-item">
                    <span className="guide-icon">{item.icon}</span>
                    <strong>{item.title}</strong>
                    <span>{item.text}</span>
                  </article>
                ))}
              </div>
            )}
          </div>
        </div>
      ) : null}
    </div>
  );
}
