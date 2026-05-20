import React, { useEffect, useMemo, useState } from "react";
import { MarimoImage } from "./components/MarimoImage";

const screens = [
  { key: "home", label: "HOME" },
  { key: "sensor", label: "SENSOR" },
  { key: "chat", label: "CHAT" },
  { key: "settings", label: "SETTINGS" },
];

const monthLabels = Array.from({ length: 12 }, (_, index) => `${index + 1}월`);

const homeNotices = [
  "오늘의 마리모 상태를 확인하고 작은 퀘스트를 완료해 주세요.",
  "빛, 물, 습도 기록은 센서 화면에서 확인할 수 있어요.",
  "체크한 퀘스트는 오늘의 돌봄 기록처럼 남겨둘 수 있어요.",
];

const questItems = [
  {
    id: "water",
    icon: "/images/incoming/icon-water.png",
    title: "물 상태 확인",
  },
  {
    id: "light",
    icon: "/images/incoming/icon-light.png",
    title: "빛 상태 확인",
  },
  {
    id: "humidity",
    icon: "/images/incoming/icon-humidity.png",
    title: "습도 확인",
  },
  {
    id: "heart",
    icon: "/images/incoming/heart_object.png",
    title: "오늘의 성장 체크",
  },
];

const sensorRangeItems = [
  { label: "온도", key: "temperature", max: 100 },
  { label: "습도", key: "humidity", max: 100 },
  { label: "수위", key: "water", max: 100 },
  { label: "조도", key: "light", max: 10000 },
];

const sensorRows = [
  { title: "온도", value: "24°C", note: "마리모가 편안하게 지내는 범위입니다." },
  { title: "습도", value: "45%", note: "주변 공기가 안정적인 상태입니다." },
  { title: "수위", value: "80%", note: "물이 충분히 채워져 있습니다." },
  { title: "조도", value: "500 lux", note: "부드러운 빛을 받고 있습니다." },
];

const guideItems = [
  { icon: "1", title: "홈", text: "마리모와 오늘의 퀘스트를 확인합니다." },
  { icon: "2", title: "센서", text: "온도, 습도, 수위, 조도 기록을 봅니다." },
  { icon: "3", title: "채팅", text: "마리모에게 현재 상태를 물어봅니다." },
  { icon: "4", title: "설정", text: "알림과 센서 범위를 조정합니다." },
];

const chatStarterMessages = [
  { id: "bot-1", role: "bot", text: "오늘도 돌봄 퀘스트를 시작해 볼까?", time: "14:31" },
  { id: "user-1", role: "user", text: "오늘 마리모 상태를 알려줘.", time: "14:32" },
  { id: "bot-2", role: "bot", text: "좋아. 물과 빛 상태를 먼저 체크해 보자.", time: "14:32" },
];

function makeWeeklySummaries(monthIndex) {
  const month = monthIndex + 1;
  const baseTemp = 23.8 + monthIndex * 0.12;
  const baseHumidity = 47 + monthIndex * 0.4;
  const baseWater = 79 + monthIndex * 0.25;
  const baseLight = 420 + monthIndex * 85;

  return [
    `${String(month).padStart(2, "0")}.01.~${String(month).padStart(2, "0")}.07. 온도 : ${(baseTemp + 0.1).toFixed(1)}°C, 습도 : ${Math.round(baseHumidity)}%, 수위 : ${Math.round(baseWater)}%, 조도 : ${Math.round(baseLight)}lux`,
    `${String(month).padStart(2, "0")}.08.~${String(month).padStart(2, "0")}.14. 온도 : ${(baseTemp + 0.4).toFixed(1)}°C, 습도 : ${Math.round(baseHumidity + 1)}%, 수위 : ${Math.round(baseWater + 1)}%, 조도 : ${Math.round(baseLight + 140)}lux`,
    `${String(month).padStart(2, "0")}.15.~${String(month).padStart(2, "0")}.21. 온도 : ${(baseTemp + 0.7).toFixed(1)}°C, 습도 : ${Math.round(baseHumidity + 2)}%, 수위 : ${Math.round(baseWater + 1)}%, 조도 : ${Math.round(baseLight + 240)}lux`,
    `${String(month).padStart(2, "0")}.22.~${String(month).padStart(2, "0")}.31. 온도 : ${(baseTemp + 0.9).toFixed(1)}°C, 습도 : ${Math.round(baseHumidity + 3)}%, 수위 : ${Math.round(baseWater + 2)}%, 조도 : ${Math.round(baseLight + 360)}lux`,
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

function Panel({ title, chip, children, className = "" }) {
  return (
    <section className={`panel ${className}`.trim()}>
      {title ? (
        <div className="panel-head">
          <strong>{title}</strong>
          {chip ? <span className="chip">{chip}</span> : <span />}
        </div>
      ) : null}
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
  const [chatMessages, setChatMessages] = useState(chatStarterMessages);
  const [openModal, setOpenModal] = useState(null);
  const [clockText, setClockText] = useState(makeClock());
  const [hoverPoint, setHoverPoint] = useState(null);
  const [checkedQuests, setCheckedQuests] = useState({});
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

  function toggleQuest(questId) {
    setCheckedQuests((current) => ({ ...current, [questId]: !current[questId] }));
  }

  function closeModal() {
    setOpenModal(null);
  }

  function sendChatMessage() {
    const message = chatDraft.trim();

    if (!message) {
      return;
    }

    setChatMessages((current) => [
      ...current,
      {
        id: `user-${Date.now()}`,
        role: "user",
        text: message,
        time: makeClock().slice(0, 5),
      },
    ]);
    setChatDraft("");
  }

  return (
    <div className="app-shell">
      <header className="app-header">
        <div className="header-inner">
          <div className="brand-block">
            <img className="brand-logo" src="/images/incoming/transparent_rogo_3.png" alt="마리모 퀘스트" />
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

          <div className="header-status">
            <div className="status-hearts" aria-hidden="true">
              <img className={notificationEnabled ? "heart on" : "heart"} src="/images/incoming/heart_object.png" alt="" />
              <img className="heart on" src="/images/incoming/heart_object.png" alt="" />
              <img className="heart on" src="/images/incoming/heart_object.png" alt="" />
            </div>
            <div className="status-clock">{clockText}</div>
          </div>
        </div>
      </header>

      <main className="app-main">
        {activeScreen === "home" && (
          <section className="home-grid">
            <Panel title="공지사항" className="panel--notice panel--transparent">
              <div className="notice-copy">
                {homeNotices.map((notice) => (
                  <p key={notice}>{notice}</p>
                ))}
              </div>
            </Panel>

            <Panel className="panel--hero panel--transparent">
              <div className="hero-stage">
                <img className="hero-bubble" src="/images/incoming/speech-bubble-horizontal.png" alt="" aria-hidden="true" />
                <div className="hero-bubble-copy">오늘도 잘 부탁해!</div>
                <MarimoImage size="large" alt="중앙 마리모 캐릭터" className="hero-marimo" />
              </div>
            </Panel>

            <Panel title="오늘의 퀘스트" className="panel--quest panel--transparent">
              <div className="quest-list">
                {questItems.map((quest) => {
                  const isChecked = Boolean(checkedQuests[quest.id]);
                  return (
                    <label key={quest.id} className={`quest-item ${isChecked ? "is-checked" : ""}`}>
                      <input
                        type="checkbox"
                        checked={isChecked}
                        onChange={() => toggleQuest(quest.id)}
                        aria-label={`${quest.title} 완료`}
                      />
                      <span className="quest-icon">
                        <img src={quest.icon} alt="" aria-hidden="true" />
                      </span>
                      <span className="quest-copy">
                        <strong>{quest.title}</strong>
                      </span>
                      <span className="quest-checkmark" aria-hidden="true">
                        {isChecked ? "완료" : "확인"}
                      </span>
                    </label>
                  );
                })}
              </div>
            </Panel>
          </section>
        )}

        {activeScreen === "sensor" && (
          <section className="sensor-stack">
            <div className="sensor-top-grid">
              <Panel className="panel--marimo">
                <div className="marimo-stage">
                  <MarimoImage size="medium" alt="센서 화면 마리모 캐릭터" className="sensor-marimo" />
                </div>
              </Panel>

              <Panel title="현재 센서 상태" className="panel--announcement panel--announcement-one">
                <div className="sensor-summary">
                  {sensorRows.map((row) => (
                    <div key={row.title} className="sensor-summary-row">
                      <div>
                        <strong>{row.title}</strong>
                      </div>
                      <div className="sensor-value">{row.value}</div>
                    </div>
                  ))}
                </div>
              </Panel>
            </div>

            <article className="sensor-switch-panel">
              <div className="panel-head">
                <h2 className="panel-title">위클릭 / 머슬릭 자료</h2>
              </div>

              <div className="panel-body">
              <div className="mode-switch">
                <button
                  type="button"
                  className={`mode-button ${sensorMode === "weekly" ? "is-active" : ""}`}
                  onClick={() => {
                    setSensorMode("weekly");
                    setHoverPoint(null);
                  }}
                >
                  Weekly
                </button>
                <button
                  type="button"
                  className={`mode-button ${sensorMode === "monthly" ? "is-active" : ""}`}
                  onClick={() => {
                    setSensorMode("monthly");
                    setHoverPoint(null);
                  }}
                >
                  Monthly
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

              <div className="sensor-content">
                {sensorMode === "weekly" ? (
                  <div className="weekly-list">
                    {weeklySummaries.map((text) => {
                      const [range, ...rest] = text.split(" ");
                      return (
                        <article key={range} className="weekly-card">
                          <span className="weekly-date">{range}</span>
                          <span className="weekly-text">{rest.join(" ")}</span>
                        </article>
                      );
                    })}
                  </div>
                ) : (
                  <div className="chart-card">
                    <div className="chart-header">
                      <h3 className="chart-title">{monthLabels[selectedChartMonth]} 머슬릭 그래프</h3>
                      <div className="legend">
                        <span className="legend-item"><span className="legend-dot legend-temp" />온도</span>
                        <span className="legend-item"><span className="legend-dot legend-humidity" />습도</span>
                        <span className="legend-item"><span className="legend-dot legend-water" />수위</span>
                        <span className="legend-item"><span className="legend-dot legend-light" />조도</span>
                      </div>
                    </div>

                    <p className="chart-caption">그래프 위에 마우스를 올리면 해당 날짜 값이 보여요.</p>

                    <div className="chart-panel">
                      <div className="chart-axis axis-left">
                        {[0, 25, 50, 75, 100].map((tick) => (
                          <span key={tick} style={{ top: `${chart.scaleY(tick, 0, 100)}px` }}>
                            {tick}
                          </span>
                        ))}
                      </div>

                      <div className="chart-viewport" onMouseLeave={() => setHoverPoint(null)} onMouseMove={handleChartMove}>
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
                            <>
                              <line x1={hoverPoint.x} x2={hoverPoint.x} y1={chart.top} y2={chart.height - chart.bottom} className="chart-crosshair" />
                              <g className="chart-hover-dots">
                                <circle className="chart-point temp-point" cx={hoverPoint.x} cy={chart.scaleY(currentPoint.temp, 0, 100)} r="2.4" />
                                <circle className="chart-point humidity-point" cx={hoverPoint.x} cy={chart.scaleY(currentPoint.humidity, 0, 100)} r="2.4" />
                                <circle className="chart-point water-point" cx={hoverPoint.x} cy={chart.scaleY(currentPoint.water, 0, 100)} r="2.4" />
                                <circle className="chart-point light-point" cx={hoverPoint.x} cy={chart.scaleY(currentPoint.light, 0, 10000)} r="2.4" />
                              </g>
                            </>
                          ) : null}
                        </svg>

                        {currentPoint ? (
                          <div
                            className="chart-tooltip"
                            style={{
                              left: `${Math.min(hoverPoint.x + 12, 66)}%`,
                              top: `${Math.min(hoverPoint.y - 48, 120)}px`,
                            }}
                          >
                            <strong>{monthLabels[selectedChartMonth]} / {currentPoint.day}일</strong>
                            <span>온도 {currentPoint.temp}°C</span>
                            <span>습도 {currentPoint.humidity}%</span>
                            <span>수위 {currentPoint.water}%</span>
                            <span>조도 {currentPoint.light.toLocaleString()} lux</span>
                          </div>
                        ) : null}
                      </div>

                      <div className="chart-axis axis-right">
                        {[10000, 7500, 5000, 2500, 0].map((tick) => (
                          <span key={`right-${tick}`} style={{ top: `${chart.scaleY(tick, 0, 10000)}px` }}>
                            {tick}
                          </span>
                        ))}
                      </div>
                    </div>
                    <div className="chart-week-labels">
                      <span>1주차</span>
                      <span>2주차</span>
                      <span>3주차</span>
                      <span>4주차</span>
                    </div>
                  </div>
                )}
              </div>
              </div>
            </article>
          </section>
        )}

        {activeScreen === "chat" && (
          <section className="chat-screen">
            <article className="chat-card">
              <div className="panel-head">
                <h2 className="panel-title">채팅</h2>
              </div>

              <div className="panel-body chat-screen-layout">
              <div className="chat-list">
                {chatMessages.map((message) => (
                  <div key={message.id} className={`chat-row ${message.role}`}>
                    {message.role === "bot" ? <MarimoImage size="small" alt="작은 마리모" className="chat-marimo" /> : null}
                    <span className="msg-time">{message.time}</span>
                    <div className={`chat-bubble ${message.role}`}>
                      <p>{message.text}</p>
                    </div>
                  </div>
                ))}
              </div>

              <div className="chat-controls">
                <textarea
                  className="chat-input"
                  value={chatDraft}
                  onChange={(event) => setChatDraft(event.target.value)}
                  onKeyDown={(event) => {
                    if (event.key === "Enter" && !event.shiftKey) {
                      event.preventDefault();
                      sendChatMessage();
                    }
                  }}
                  placeholder={chatMode === "음성" ? "음성 모드에서 말하고 싶은 내용을 적어도 돼요." : "메시지를 입력해 주세요."}
                />
                <button type="button" className="send-button" onClick={sendChatMessage}>전송</button>
                <button
                  type="button"
                  className="voice-button"
                  onClick={() => setChatMode((current) => (current === "텍스트" ? "음성" : "텍스트"))}
                >
                  {chatMode === "텍스트" ? "음성" : "텍스트"}
                </button>
              </div>
              </div>
            </article>
          </section>
        )}

        {activeScreen === "settings" && (
          <section className="settings-screen">
            <div className="settings-grid">
              <button
                type="button"
                className={`notification-toggle ${notificationEnabled ? "is-on" : "is-off"}`}
                onClick={() => setNotificationEnabled((current) => !current)}
              >
                {notificationEnabled ? "on" : "off"}
              </button>

              <button type="button" className="setting-button" onClick={() => setOpenModal("sensor")}>
                <div className="setting-title">센서</div>
              </button>

              <button type="button" className="setting-button" onClick={() => setOpenModal("guide")}>
                <div className="setting-title">가이드</div>
              </button>
            </div>
          </section>
        )}
      </main>

      {openModal ? (
        <div className="modal-backdrop" onClick={(event) => event.target === event.currentTarget && closeModal()}>
          <div className="modal-card" role="dialog" aria-modal="true">
            <div className="modal-head">
              {openModal === "sensor" ? (
                <h2 className="modal-title">센서값 지정</h2>
              ) : (
                <h2 className="modal-title">마리모 가이드</h2>
              )}
              <button type="button" className="modal-close" onClick={closeModal}>×</button>
            </div>

            {openModal === "sensor" ? (
              <div className="modal-body">
                <div className="range-list">
                  {sensorRangeItems.map((item) => {
                    const minKey = `${item.key}Min`;
                    const maxKey = `${item.key}Max`;
                    const minValue = sensorRanges[minKey];
                    const maxValue = sensorRanges[maxKey];

                    return (
                      <div key={item.key} className="range-row">
                        <div className="range-head">
                          <span>{item.label}</span>
                          <strong>{minValue} ~ {maxValue}</strong>
                        </div>
                        <div
                          className="range-bar"
                          onPointerDown={(event) => {
                            const rect = event.currentTarget.getBoundingClientRect();
                            const ratio = Math.max(0, Math.min(1, (event.clientX - rect.left) / rect.width));
                            const nextValue = Math.round(ratio * item.max);
                            const minDistance = Math.abs(nextValue - minValue);
                            const maxDistance = Math.abs(nextValue - maxValue);

                            if (minDistance <= maxDistance) {
                              setSensorRanges((current) => ({ ...current, [minKey]: Math.min(nextValue, current[maxKey]) }));
                            } else {
                              setSensorRanges((current) => ({ ...current, [maxKey]: Math.max(nextValue, current[minKey]) }));
                            }
                          }}
                        >
                          <div
                            className="range-fill"
                            style={{
                              left: `${(minValue / item.max) * 100}%`,
                              width: `${((maxValue - minValue) / item.max) * 100}%`,
                            }}
                          />
                          <input
                            className="range-input"
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
                            className="range-input"
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
                      </div>
                    );
                  })}
                </div>
              </div>
            ) : (
              <div className="modal-body">
                <div className="guide-grid">
                  {guideItems.map((item) => (
                    <article key={item.title} className="guide-item">
                      <span className="guide-icon">{item.icon}</span>
                      <strong>{item.title}</strong>
                      <span>{item.text}</span>
                    </article>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      ) : null}
    </div>
  );
}
