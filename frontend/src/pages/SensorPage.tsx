import { type MouseEvent, useMemo, useState } from 'react';
import '../styles/sensor.css';

type ViewMode = 'weekly' | 'monthly';

type ChartRow = {
  label: string;
  title: string;
  dateRange: string;
  temperature: number;
  humidity: number;
  water: number;
  light: number;
  temperatureChart: number;
  humidityChart: number;
  waterChart: number;
  lightChart: number;
};

type WeeklyMetric = {
  label: string;
  value: string;
  progress: number;
  icon: string;
  tone: 'temperature' | 'humidity' | 'water' | 'light';
  weeklyValues: number[];
};

type WeeklyRow = {
  weekLabel: string;
  dateRange: string;
  moodTone: 'good' | 'great';
  moodState: 'happy' | 'neutral' | 'sad';
  moodReaction: 'GREAT' | 'SOSO' | 'SAD';
  issueCount: number;
  metrics: WeeklyMetric[];
};

type SensorStatusItem = {
  label: string;
  value: string;
  suffix: string;
  icon: string;
  tone: 'green' | 'blue' | 'teal' | 'gold';
};

type ChartSeries = {
  label: string;
  color: string;
  values: number[];
};

const SENSOR_STATUS_ITEMS: SensorStatusItem[] = [
  { label: '온도', value: '24', suffix: '℃', icon: '/images/incoming/icon_temperature.png', tone: 'green' },
  { label: '습도', value: '45', suffix: '%', icon: '/images/incoming/icon-humidity.png', tone: 'blue' },
  { label: '수위', value: '80', suffix: '%', icon: '/images/incoming/icon-water.png', tone: 'teal' },
  { label: '조도', value: '500', suffix: 'lux', icon: '/images/incoming/icon-light.png', tone: 'gold' },
];

const MONTHS = ['1월', '2월', '3월', '4월', '5월', '6월', '7월', '8월', '9월', '10월', '11월', '12월'];

const VIEW_TABS: { key: ViewMode; label: string }[] = [
  { key: 'weekly', label: 'weekly' },
  { key: 'monthly', label: 'monthly' },
];

const CHART_SIZE = { width: 980, height: 380 };
const CHART_PADDING = { top: 28, right: 46, bottom: 54, left: 66 };
const CHART_Y_TICKS = [0, 25, 50, 75, 100];
const CHART_X_TICKS = [
  { label: '0', index: 0 },
  { label: '1주차', index: 6 },
  { label: '2주차', index: 13 },
  { label: '3주차', index: 20 },
  { label: '4주차', index: 27 },
  { label: '5주차', index: 30 },
];

function clamp(value: number, min: number, max: number) {
  return Math.max(min, Math.min(value, max));
}

function round1(value: number) {
  return Math.round(value * 10) / 10;
}

function formatMonthPointLabel(month: number, index: number) {
  return `${month}월 ${index + 1}주차`;
}

function getWeeklyMoodState(issueCount: number): WeeklyRow['moodState'] {
  if (issueCount >= 3) return 'sad';
  if (issueCount >= 1) return 'neutral';
  return 'happy';
}

type WeeklyHover = {
  weekLabel: string;
  metricLabel: string;
  valueLabel: string;
  tone: WeeklyMetric['tone'];
  pointIndex: number;
  x: number;
  y: number;
  sparkWidth: number;
  sparkHeight: number;
};

// 실제 센서가 아니라, UI를 보여주기 위한 예시 데이터만 만들어준다.
// 월이 바뀌면 숫자도 함께 살짝 달라져서 화면이 살아 보이도록 만든다.
function buildChartRows(month: number): ChartRow[] {
  const monthSeed = month - 1;
  const baseMonth = String(month).padStart(2, '0');

  return Array.from({ length: 31 }, (_, index) => {
    const day = index + 1;
    const wave = Math.sin((monthSeed + day) * 0.45);
    const drift = Math.cos((monthSeed + day) * 0.32);

    const temperature = round1(23.4 + monthSeed * 0.12 + day * 0.04 + wave * 0.65);
    const humidity = round1(44.8 + monthSeed * 0.16 + day * 0.08 + drift * 0.75);
    const water = round1(79.5 - monthSeed * 0.08 + day * 0.05 + wave * 0.55);
    const light = Math.round(460 + monthSeed * 12 + day * 9 + drift * 36);

    return {
      label: `${day}일`,
      title: `${month}월 ${day}일`,
      dateRange: `${baseMonth}.${String(day).padStart(2, '0')}`,
      temperature,
      humidity,
      water,
      light,
      temperatureChart: clamp(Math.round((temperature / 30) * 100), 0, 100),
      humidityChart: clamp(Math.round(humidity), 0, 100),
      waterChart: clamp(Math.round(water), 0, 100),
      lightChart: clamp(Math.round((light / 1200) * 100), 0, 100),
    };
  });
}

// 주간 기록 화면은 스크린샷처럼 행 단위로 보여준다.
function buildWeeklyRows(month: number): WeeklyRow[] {
  const baseMonth = String(month).padStart(2, '0');
  const monthlyShift = month - 5;

  const baseRows = [
    {
      weekLabel: 'WEEK 1',
      dateRange: `${baseMonth}.01 ~ ${baseMonth}.07`,
      moodLabel: 'GOOD',
      moodTone: 'good' as const,
      temperature: 24.4,
      humidity: 49,
      water: 80,
      light: 760,
    },
    {
      weekLabel: 'WEEK 2',
      dateRange: `${baseMonth}.08 ~ ${baseMonth}.14`,
      moodLabel: 'GOOD',
      moodTone: 'good' as const,
      temperature: 24.7,
      humidity: 50,
      water: 81,
      light: 900,
    },
    {
      weekLabel: 'WEEK 3',
      dateRange: `${baseMonth}.15 ~ ${baseMonth}.21`,
      moodLabel: 'GREAT',
      moodTone: 'great' as const,
      temperature: 25.0,
      humidity: 51,
      water: 81,
      light: 1000,
    },
    {
      weekLabel: 'WEEK 4',
      dateRange: `${baseMonth}.22 ~ ${baseMonth}.31`,
      moodLabel: 'GREAT',
      moodTone: 'great' as const,
      temperature: 25.2,
      humidity: 52,
      water: 82,
      light: 1120,
    },
  ];

  return baseRows.map((row, index) => {
    const shift = monthlyShift * 0.08;
    const tempValue = round1(row.temperature + shift + index * 0.03);
    const humidityValue = Math.round(row.humidity + monthlyShift * 0.35 + index * 0.15);
    const waterValue = Math.round(row.water + monthlyShift * 0.18 + index * 0.12);
    const lightValue = Math.round(row.light + monthlyShift * 24 + index * 18);
    const issueCount =
      Number(tempValue < 24.1 || tempValue > 25.4) +
      Number(humidityValue < 48 || humidityValue > 52) +
      Number(waterValue < 79 || waterValue > 83) +
      Number(lightValue < 720 || lightValue > 1150);
    const moodState = index === 0 ? 'happy' : index === 1 ? 'neutral' : index === 2 ? 'sad' : getWeeklyMoodState(issueCount);

    return {
      weekLabel: row.weekLabel,
      dateRange: row.dateRange,
      moodTone: row.moodTone,
      moodState,
      moodReaction: moodState === 'sad' ? 'SAD' : moodState === 'neutral' ? 'SOSO' : 'GREAT',
      issueCount,
      metrics: [
        {
          label: '온도',
          value: `${tempValue}℃`,
          progress: clamp(Math.round((tempValue / 30) * 100), 0, 100),
          icon: '/images/incoming/icon_temperature.png',
          tone: 'temperature',
          weeklyValues: [
            Math.max(0, tempValue - 0.6),
            Math.max(0, tempValue - 0.3),
            tempValue,
            tempValue + 0.2,
            tempValue + 0.1,
            tempValue + 0.35,
            tempValue + 0.5,
          ].map((value) => Math.round(value * 10) / 10),
        },
        {
          label: '습도',
          value: `${humidityValue}%`,
          progress: clamp(humidityValue, 0, 100),
          icon: '/images/incoming/icon-humidity.png',
          tone: 'humidity',
          weeklyValues: [humidityValue - 2, humidityValue - 1, humidityValue, humidityValue + 1, humidityValue + 1, humidityValue + 2, humidityValue + 1],
        },
        {
          label: '수위',
          value: `${waterValue}%`,
          progress: clamp(waterValue, 0, 100),
          icon: '/images/incoming/icon-water.png',
          tone: 'water',
          weeklyValues: [waterValue + 1, waterValue + 1, waterValue, waterValue + 2, waterValue + 1, waterValue + 3, waterValue + 2],
        },
        {
          label: '조도',
          value: `${lightValue} lux`,
          progress: clamp(Math.round((lightValue / 1200) * 100), 0, 100),
          icon: '/images/incoming/icon-light.png',
          tone: 'light',
          weeklyValues: [lightValue - 24, lightValue - 10, lightValue - 4, lightValue + 8, lightValue + 14, lightValue + 22, lightValue + 30],
        },
      ],
    };
  });
}

// 점들을 부드러운 곡선으로 연결하는 헬퍼.
function buildSmoothPath(points: { x: number; y: number }[]): string {
  if (points.length === 0) return '';
  if (points.length === 1) return `M ${points[0].x} ${points[0].y}`;

  let path = `M ${points[0].x} ${points[0].y}`;

  for (let index = 0; index < points.length - 1; index += 1) {
    const current = points[index];
    const next = points[index + 1];
    const cpX1 = current.x + (next.x - current.x) / 3;
    const cpY1 = current.y;
    const cpX2 = current.x + ((next.x - current.x) * 2) / 3;
    const cpY2 = next.y;
    path += ` C ${cpX1} ${cpY1}, ${cpX2} ${cpY2}, ${next.x} ${next.y}`;
  }

  return path;
}

function buildSeries(rows: ChartRow[]): ChartSeries[] {
  return [
    { label: '온도', color: '#e85b50', values: rows.map((row) => row.temperatureChart) },
    { label: '습도', color: '#2f90d1', values: rows.map((row) => row.humidityChart) },
    { label: '수위', color: '#21a87e', values: rows.map((row) => row.waterChart) },
    { label: '조도', color: '#d38a20', values: rows.map((row) => row.lightChart) },
  ];
}

function formatValue(label: string, row: ChartRow): string {
  switch (label) {
    case '온도':
      return `${row.temperature}℃`;
    case '습도':
      return `${row.humidity}%`;
    case '수위':
      return `${row.water}%`;
    case '조도':
      return `${row.light} lux`;
    default:
      return '-';
  }
}

export function SensorPage() {
  const [viewMode, setViewMode] = useState<ViewMode>('weekly');
  const [selectedMonth, setSelectedMonth] = useState(5);
  const [hoveredIndex, setHoveredIndex] = useState<number | null>(null);
  const [weeklyHover, setWeeklyHover] = useState<WeeklyHover | null>(null);
  const [weeklyPinnedHover, setWeeklyPinnedHover] = useState<WeeklyHover | null>(null);

  const chartRows = useMemo(() => buildChartRows(selectedMonth), [selectedMonth]);
  const weeklyRows = useMemo(() => buildWeeklyRows(selectedMonth), [selectedMonth]);
  const series = useMemo(() => buildSeries(chartRows), [chartRows]);

  const chartPlotWidth = CHART_SIZE.width - CHART_PADDING.left - CHART_PADDING.right;
  const chartPlotHeight = CHART_SIZE.height - CHART_PADDING.top - CHART_PADDING.bottom;
  const stepX = chartRows.length > 1 ? chartPlotWidth / (chartRows.length - 1) : chartPlotWidth;

  const pointsBySeries = series.map((item) =>
    item.values.map((value, index) => {
      const x = CHART_PADDING.left + stepX * index;
      const y = CHART_PADDING.top + chartPlotHeight - (value / 100) * chartPlotHeight;
      return { x, y };
    }),
  );

  const activePoint = hoveredIndex !== null ? chartRows[hoveredIndex] : null;

  const handleMouseMove = (event: MouseEvent<SVGSVGElement>) => {
    if (chartRows.length === 0) return;

    const rect = event.currentTarget.getBoundingClientRect();
    const mouseX = ((event.clientX - rect.left) / rect.width) * CHART_SIZE.width;

    let closestIndex = 0;
    let closestDistance = Number.POSITIVE_INFINITY;

    chartRows.forEach((_, index) => {
      const pointX = CHART_PADDING.left + stepX * index;
      const distance = Math.abs(pointX - mouseX);
      if (distance < closestDistance) {
        closestDistance = distance;
        closestIndex = index;
      }
    });

    setHoveredIndex(closestIndex);
  };

  const handleMouseLeave = () => {
    setHoveredIndex(null);
  };

  const activeMonthLabel = `${selectedMonth}월`;
  const reportTitle = viewMode === 'weekly' ? '마리모 성장 기록장' : '마리모 월간 성장 리포트';
  const chartTitle = `${activeMonthLabel} 성장 그래프`;
  const activeWeeklyHover = weeklyHover ?? weeklyPinnedHover;

  const tooltipWidth = 232;
  const tooltipHeight = 128;

  return (
    <div className="sensor-page">
      <div className="sensor-page__inner">
        {/* 현재 센서 상태 패널 */}
        <section className="sensor-panel sensor-panel--status" aria-label="현재 센서 상태">
          <div className="sensor-status-bar" role="list" aria-label="현재 센서 상태 요약">
            {SENSOR_STATUS_ITEMS.map((item) => (
              <div key={item.label} className="sensor-status-item" role="listitem">
                <span className={`sensor-status-item__icon sensor-status-item__icon--${item.tone}`} aria-hidden="true">
                  <img src={item.icon} alt="" />
                </span>
                <span className="sensor-status-item__label">{item.label}</span>
                <span className="sensor-status-item__value">
                  {item.value}
                  <span className="sensor-status-item__suffix">{item.suffix}</span>
                </span>
              </div>
            ))}
          </div>
        </section>

        {/* 성장 기록 메인 박스 */}
        <section className="sensor-panel sensor-panel--report" aria-label="마리모 성장 기록">
          <div className="sensor-report-frame">
            <div className="sensor-report-frame__inner">
                <div className="sensor-report-hero">
                  <img className="sensor-report-hero__marimo-image" src="/images/incoming/marimo-shadow-medium.png" alt="" aria-hidden="true" />
                  <div className="sensor-report-copy">
                    <h2 className="sensor-report-copy__title">{reportTitle}</h2>
                  </div>
                </div>

              <div className="sensor-report-tabs" role="tablist" aria-label="리포트 보기 방식">
                {VIEW_TABS.map((tab) => {
                  const active = viewMode === tab.key;
                  return (
                    <button
                      key={tab.key}
                      type="button"
                      className={`sensor-report-tab ${active ? 'is-active' : ''}`}
                      aria-pressed={active}
                      onClick={() => {
                        setViewMode(tab.key);
                        setHoveredIndex(null);
                      }}
                    >
                      {tab.label}
                    </button>
                  );
                })}
              </div>

              <div className="sensor-month-picker" aria-label="월 선택">
                {MONTHS.map((monthLabel, index) => {
                  const monthNumber = index + 1;
                  const active = monthNumber === selectedMonth;
                  return (
                    <button
                      key={monthLabel}
                      type="button"
                      className={`sensor-month-chip ${active ? 'is-active' : ''}`}
                      aria-pressed={active}
                      onClick={() => {
                        setSelectedMonth(monthNumber);
                        setHoveredIndex(null);
                        setWeeklyHover(null);
                        setWeeklyPinnedHover(null);
                      }}
                    >
                      {monthLabel}
                    </button>
                  );
                })}
              </div>

              {viewMode === 'weekly' ? (
                <section className="sensor-weekly-log" aria-label={`${activeMonthLabel} 주간 기록`}>
                  {weeklyRows.map((row, rowIndex) => (
                    <article key={row.weekLabel} className={`sensor-weekly-row sensor-weekly-row--${row.moodTone}`}>
                      <div className="sensor-weekly-row__left">
                        <div className="sensor-weekly-row__banner">{row.weekLabel}</div>
                        <div className={`sensor-weekly-row__date ${rowIndex === 0 ? 'sensor-weekly-row__date--large' : ''}`}>{row.dateRange}</div>
                      </div>

                      <div className="sensor-weekly-row__mood" aria-label={row.moodLabel}>
                        <div className={`sensor-weekly-row__marimo sensor-weekly-row__marimo--${row.moodState}`} aria-hidden="true">
                          <img
                            className="sensor-weekly-row__marimo-image"
                            src={
                              row.moodState === 'sad'
                                ? '/images/incoming/sad.png'
                                : row.moodState === 'neutral'
                                  ? '/images/incoming/expressionless.png'
                                  : '/images/incoming/smail2.png'
                            }
                            alt=""
                            aria-hidden="true"
                          />
                        </div>
                        <div className="sensor-weekly-row__mood-reaction">{row.moodReaction}</div>
                      </div>

                      <div className="sensor-weekly-row__metrics">
                        {row.metrics.map((metric) => {
                          const sparkMin = Math.min(...metric.weeklyValues);
                          const sparkMax = Math.max(...metric.weeklyValues);
                          const sparkWidth = 190;
                          const sparkHeight = 44;
                          const sparkPadding = 4;
                          const sparkStep = metric.weeklyValues.length > 1 ? (sparkWidth - sparkPadding * 2) / (metric.weeklyValues.length - 1) : sparkWidth;
                          const sparkPoints = metric.weeklyValues
                            .map((value, index) => {
                              const range = sparkMax - sparkMin || 1;
                              const x = sparkPadding + sparkStep * index;
                              const y = sparkPadding + (sparkHeight - sparkPadding * 2) - ((value - sparkMin) / range) * (sparkHeight - sparkPadding * 2);
                              return `${x},${y}`;
                            })
                            .join(' ');

                          return (
                            <div key={metric.label} className="sensor-weekly-metric">
                              <div className="sensor-weekly-metric__head">
                                <span className={`sensor-weekly-metric__icon sensor-weekly-metric__icon--${metric.tone}`} aria-hidden="true">
                                  <img src={metric.icon} alt="" />
                                </span>
                                <span className="sensor-weekly-metric__label">{metric.label}</span>
                                <span
                                  className={`sensor-weekly-metric__value ${
                                    activeWeeklyHover?.weekLabel === row.weekLabel && activeWeeklyHover?.metricLabel === metric.label ? 'is-hovered' : ''
                                  }`}
                                >
                                  {activeWeeklyHover?.weekLabel === row.weekLabel && activeWeeklyHover?.metricLabel === metric.label
                                    ? activeWeeklyHover.valueLabel
                                    : metric.value}
                                </span>
                              </div>

                              <div className="sensor-weekly-metric__spark" aria-hidden="true">
                                <svg viewBox={`0 0 ${sparkWidth} ${sparkHeight}`} className="sensor-weekly-metric__spark-svg">
                                  <polyline points={sparkPoints} className={`sensor-weekly-metric__spark-line sensor-weekly-metric__spark-line--${metric.tone}`} />
                                  {metric.weeklyValues.map((value, index) => {
                                    const range = sparkMax - sparkMin || 1;
                                    const x = sparkPadding + sparkStep * index;
                                    const y = sparkPadding + (sparkHeight - sparkPadding * 2) - ((value - sparkMin) / range) * (sparkHeight - sparkPadding * 2);
                                    const valueLabel = metric.label === '온도' ? `${value}℃` : metric.label === '조도' ? `${value} lux` : `${value}%`;
                                    const isActive =
                                      activeWeeklyHover?.weekLabel === row.weekLabel &&
                                      activeWeeklyHover?.metricLabel === metric.label &&
                                      activeWeeklyHover?.pointIndex === index;

                                    return (
                                      <circle
                                        key={`${metric.label}-${index}`}
                                        cx={x}
                                        cy={y}
                                        r={isActive ? '4.2' : '2.8'}
                                        className={`sensor-weekly-metric__spark-dot sensor-weekly-metric__spark-dot--${metric.tone}`}
                                        onMouseEnter={() =>
                                          setWeeklyHover({
                                            weekLabel: row.weekLabel,
                                            metricLabel: metric.label,
                                            valueLabel,
                                            tone: metric.tone,
                                            pointIndex: index,
                                            x,
                                            y,
                                            sparkWidth,
                                            sparkHeight,
                                          })
                                        }
                                        onClick={() =>
                                          setWeeklyPinnedHover({
                                            weekLabel: row.weekLabel,
                                            metricLabel: metric.label,
                                            valueLabel,
                                            tone: metric.tone,
                                            pointIndex: index,
                                            x,
                                            y,
                                            sparkWidth,
                                            sparkHeight,
                                          })
                                        }
                                        onMouseLeave={() => setWeeklyHover(null)}
                                      />
                                    );
                                  })}
                                </svg>
                              </div>
                            </div>
                          );
                        })}
                      </div>
                    </article>
                  ))}
                </section>
              ) : (
                <section className="sensor-graph-card" aria-label="성장 그래프">
                  <div className="sensor-graph-card__header">
                    <div className="sensor-graph-card__copy">
                      <h3 className="sensor-graph-card__title">{chartTitle}</h3>
                    </div>

                    <div className="sensor-graph-badges" aria-label="상태 배지">
                      <span className="sensor-graph-badge sensor-graph-badge--temperature">온도</span>
                      <span className="sensor-graph-badge sensor-graph-badge--humidity">습도</span>
                      <span className="sensor-graph-badge sensor-graph-badge--water">수위</span>
                      <span className="sensor-graph-badge sensor-graph-badge--light">조도</span>
                    </div>
                  </div>

                  <div className="sensor-chart-shell">
                    <svg
                      className="sensor-chart-shell__svg"
                      viewBox={`0 0 ${CHART_SIZE.width} ${CHART_SIZE.height}`}
                      role="img"
                      aria-label={chartTitle}
                      onMouseMove={handleMouseMove}
                      onMouseLeave={handleMouseLeave}
                    >
                      <defs>
                        <linearGradient id="temperature-fill" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="0%" stopColor="#e85b50" stopOpacity="0.24" />
                          <stop offset="100%" stopColor="#e85b50" stopOpacity="0" />
                        </linearGradient>
                        <linearGradient id="humidity-fill" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="0%" stopColor="#2f90d1" stopOpacity="0.24" />
                          <stop offset="100%" stopColor="#2f90d1" stopOpacity="0" />
                        </linearGradient>
                        <linearGradient id="water-fill" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="0%" stopColor="#21a87e" stopOpacity="0.24" />
                          <stop offset="100%" stopColor="#21a87e" stopOpacity="0" />
                        </linearGradient>
                        <linearGradient id="light-fill" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="0%" stopColor="#d38a20" stopOpacity="0.24" />
                          <stop offset="100%" stopColor="#d38a20" stopOpacity="0" />
                        </linearGradient>
                      </defs>

                      {CHART_Y_TICKS.map((tick) => {
                        const y = CHART_PADDING.top + chartPlotHeight - (tick / 100) * chartPlotHeight;
                        return (
                          <g key={tick}>
                            <line
                              x1={CHART_PADDING.left}
                              x2={CHART_SIZE.width - CHART_PADDING.right}
                              y1={y}
                              y2={y}
                              className="sensor-chart-shell__grid-line"
                            />
                            <text
                              x={CHART_PADDING.left - 14}
                              y={y + 4}
                              textAnchor="end"
                              className="sensor-chart-shell__axis-label"
                            >
                              {tick}
                            </text>
                            <text
                              x={CHART_SIZE.width - CHART_PADDING.right + 16}
                              y={y + 4}
                              textAnchor="start"
                              className="sensor-chart-shell__axis-label sensor-chart-shell__axis-label--transparent"
                              aria-hidden="true"
                            >
                              {tick}
                            </text>
                          </g>
                        );
                      })}

                      <line
                        x1={CHART_PADDING.left}
                        y1={CHART_PADDING.top}
                        x2={CHART_PADDING.left}
                        y2={CHART_SIZE.height - CHART_PADDING.bottom}
                        className="sensor-chart-shell__axis"
                      />
                      <line
                        x1={CHART_PADDING.left}
                        y1={CHART_SIZE.height - CHART_PADDING.bottom}
                        x2={CHART_SIZE.width - CHART_PADDING.right}
                        y2={CHART_SIZE.height - CHART_PADDING.bottom}
                        className="sensor-chart-shell__axis"
                      />

                      {CHART_X_TICKS.map((tick) => {
                        const x = CHART_PADDING.left + stepX * tick.index;
                        return (
                          <text
                            key={tick.label}
                            x={x}
                            y={CHART_SIZE.height - 18}
                            textAnchor="middle"
                            className="sensor-chart-shell__week-label"
                          >
                            {tick.label}
                          </text>
                        );
                      })}

                      {series.map((item, seriesIndex) => {
                        const points = pointsBySeries[seriesIndex];
                        const path = buildSmoothPath(points);
                        return (
                          <g key={item.label}>
                            <path
                              d={path}
                              fill="none"
                              stroke={item.color}
                              strokeWidth="4.5"
                              strokeLinecap="round"
                              strokeLinejoin="round"
                            />
                          </g>
                        );
                      })}

                      {hoveredIndex !== null && activePoint && (
                        <g>
                          {(() => {
                            const x = CHART_PADDING.left + stepX * hoveredIndex;
                            return (
                              <>
                                <line
                                  x1={x}
                                  y1={CHART_PADDING.top}
                                  x2={x}
                                  y2={CHART_SIZE.height - CHART_PADDING.bottom}
                                  stroke="#7a4b24"
                                  strokeOpacity="0.34"
                                  strokeDasharray="4 4"
                                  strokeWidth="2"
                                />

                                {series.map((item, seriesIndex) => {
                                  const point = pointsBySeries[seriesIndex][hoveredIndex];
                                  return (
                                    <circle
                                      key={`${item.label}-hover-${hoveredIndex}`}
                                      cx={point.x}
                                      cy={point.y}
                                      r="6"
                                      fill={item.color}
                                      stroke="#fff8e7"
                                      strokeWidth="2"
                                    />
                                  );
                                })}

                                {(() => {
                                  const tooltipX = x + tooltipWidth + 20 > CHART_SIZE.width ? x - tooltipWidth - 20 : x + 18;
                                  const tooltipY = CHART_PADDING.top + 18;
                                  return (
                                    <g transform={`translate(${tooltipX}, ${tooltipY})`}>
                                      <rect
                                        width={tooltipWidth}
                                        height={tooltipHeight}
                                        rx="14"
                                        fill="#fff8e7"
                                        stroke="rgba(109, 68, 31, 0.24)"
                                        strokeWidth="2.5"
                                        style={{ filter: 'drop-shadow(0 8px 16px rgba(88,49,22,0.12))' }}
                                      />
                                      <text x="14" y="22" className="sensor-chart-tooltip__title">
                                        {activePoint.title}
                                      </text>
                                      <text x="14" y="42" className="sensor-chart-tooltip__meta">
                                        {activePoint.dateRange}
                                      </text>
                                      <text x="14" y="64" className="sensor-chart-tooltip__line">
                                        온도
                                        <tspan dx="8" className="sensor-chart-tooltip__value sensor-chart-tooltip__value--temperature">
                                          {formatValue('온도', activePoint)}
                                        </tspan>
                                      </text>
                                      <text x="14" y="82" className="sensor-chart-tooltip__line">
                                        습도
                                        <tspan dx="8" className="sensor-chart-tooltip__value sensor-chart-tooltip__value--humidity">
                                          {formatValue('습도', activePoint)}
                                        </tspan>
                                      </text>
                                      <text x="14" y="100" className="sensor-chart-tooltip__line">
                                        수위
                                        <tspan dx="8" className="sensor-chart-tooltip__value sensor-chart-tooltip__value--water">
                                          {formatValue('수위', activePoint)}
                                        </tspan>
                                      </text>
                                      <text x="14" y="118" className="sensor-chart-tooltip__line">
                                        조도
                                        <tspan dx="8" className="sensor-chart-tooltip__value sensor-chart-tooltip__value--light">
                                          {formatValue('조도', activePoint)}
                                        </tspan>
                                      </text>
                                    </g>
                                  );
                                })()}
                              </>
                            );
                          })()}
                        </g>
                      )}
                    </svg>
                  </div>
                </section>
              )}
            </div>
          </div>
        </section>
      </div>
    </div>
  );
}
