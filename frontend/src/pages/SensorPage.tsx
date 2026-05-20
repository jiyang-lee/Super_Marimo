import '../styles/sensor.css';
import { useEffect, useState } from 'react';
import { getLatestSensor, getSensorHistory, type SensorLatest, type SensorReading } from '../api';

type SensorKey = 'temperature' | 'humidity' | 'light' | 'water_level' | 'distance';

const TAB_CONFIGS = {
  temperature: { label: '온도', suffix: '°C', stroke: '#e11d48', fillStart: 'rgba(225, 29, 72, 0.25)', fillEnd: 'rgba(225, 29, 72, 0)' },
  humidity: { label: '습도', suffix: '%', stroke: '#0284c7', fillStart: 'rgba(2, 132, 199, 0.25)', fillEnd: 'rgba(2, 132, 199, 0)' },
  light: { label: '조도', suffix: 'lux', stroke: '#d97706', fillStart: 'rgba(217, 119, 6, 0.25)', fillEnd: 'rgba(217, 119, 6, 0)' },
  water_level: { label: '수위(raw)', suffix: '', stroke: '#0d9488', fillStart: 'rgba(13, 148, 136, 0.25)', fillEnd: 'rgba(13, 148, 136, 0)' },
  distance: { label: '거리', suffix: 'cm', stroke: '#4f46e5', fillStart: 'rgba(79, 70, 229, 0.25)', fillEnd: 'rgba(79, 70, 229, 0)' },
} as const;

function Card({
  label,
  value,
  suffix,
}: {
  label: string;
  value: string | number | null | undefined;
  suffix?: string;
}) {
  const text = value === null || value === undefined || value === '' ? '-' : `${value}${suffix ?? ''}`;
  return (
    <div className="rounded-[1.4rem] border-4 border-bark/10 bg-white/90 p-4 shadow-sm">
      <div className="font-dot text-xs uppercase tracking-wider text-bark/50">{label}</div>
      <div className="mt-2 text-3xl font-black text-bark">{text}</div>
    </div>
  );
}

function formatState(state: string | null | undefined): string {
  if (!state) return '데이터 없음';
  if (state === 'normal') return '괜찮음';
  if (state === 'warning') return '주의';
  if (state === 'danger') return '위험';
  return state;
}

function formatTime(isoString?: string): string {
  if (!isoString) return '';
  try {
    const d = new Date(isoString);
    const mm = String(d.getMonth() + 1).padStart(2, '0');
    const dd = String(d.getDate()).padStart(2, '0');
    const hh = String(d.getHours()).padStart(2, '0');
    const min = String(d.getMinutes()).padStart(2, '0');
    return `${mm}-${dd} ${hh}:${min}`;
  } catch {
    return '';
  }
}

function formatTickLabel(date: Date): string {
  const mm = String(date.getMonth() + 1).padStart(2, '0');
  const dd = String(date.getDate()).padStart(2, '0');
  const hh = String(date.getHours()).padStart(2, '0');
  const min = String(date.getMinutes()).padStart(2, '0');
  return `${mm}-${dd} ${hh}:${min}`;
}

// Cubic Bezier curve generator
function getCurvePath(points: { x: number; y: number }[]): string {
  if (points.length === 0) return '';
  if (points.length === 1) return `M ${points[0].x} ${points[0].y}`;

  let d = `M ${points[0].x} ${points[0].y}`;
  for (let i = 0; i < points.length - 1; i++) {
    const p0 = points[i];
    const p1 = points[i + 1];
    const cpX1 = p0.x + (p1.x - p0.x) / 3;
    const cpY1 = p0.y;
    const cpX2 = p0.x + (2 * (p1.x - p0.x)) / 3;
    const cpY2 = p1.y;
    d += ` C ${cpX1} ${cpY1}, ${cpX2} ${cpY2}, ${p1.x} ${p1.y}`;
  }
  return d;
}

export function SensorPage() {
  const [sensor, setSensor] = useState<SensorLatest | null>(null);
  const [history, setHistory] = useState<SensorReading[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [activeTab, setActiveTab] = useState<SensorKey>('temperature');

  // Interactive Graph Hover State
  const [hoveredIndex, setHoveredIndex] = useState<number | null>(null);

  const load = async () => {
    setLoading(true);
    setError('');
    try {
      const [latestResult, historyResult] = await Promise.all([
        getLatestSensor(),
        getSensorHistory(120),
      ]);
      setSensor(latestResult);
      setHistory(historyResult.realtime_history ?? []);
    } catch (e) {
      setError(e instanceof Error ? e.message : '센서 정보를 불러오지 못했어요.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void load();
    const timer = setInterval(() => void load(), 5000);
    return () => clearInterval(timer);
  }, []);

  const realtime = sensor?.latest_realtime ?? null;
  const hasData =
    realtime?.temperature !== undefined ||
    realtime?.humidity !== undefined ||
    realtime?.light !== undefined ||
    realtime?.water_level !== undefined ||
    realtime?.distance !== undefined;

  // Chart configuration
  const paddingLeft = 70;
  const paddingRight = 30;
  const paddingTop = 40;
  const paddingBottom = 50;

  const activeConfig = TAB_CONFIGS[activeTab];

  // Raw history data for the selected sensor type
  const chartPointsRaw = history
    .map((item) => {
      const val = item[activeTab];
      return { val, date: item.created_at };
    })
    .filter((p): p is { val: number; date: string | undefined } => p.val !== undefined && p.val !== null)
    .sort((a, b) => {
      const aTime = a.date ? new Date(a.date).getTime() : 0;
      const bTime = b.date ? new Date(b.date).getTime() : 0;
      return aTime - bTime;
    });

  const tickStepHours = 2;
  const tickStepMs = tickStepHours * 60 * 60 * 1000;
  const timestamps = chartPointsRaw
    .map((point) => {
      if (!point.date) return null;
      const time = new Date(point.date).getTime();
      return Number.isFinite(time) ? time : null;
    })
    .filter((time): time is number => time !== null);

  const timeDomainStart =
    timestamps.length > 0 ? new Date(Math.min(...timestamps)).getTime() : null;
  const timeDomainEnd =
    timestamps.length > 0 ? new Date(Math.max(...timestamps)).getTime() : null;
  const alignedDomainStart = timeDomainStart !== null ? Math.floor(timeDomainStart / tickStepMs) * tickStepMs : null;
  const alignedDomainEnd = timeDomainEnd !== null ? Math.ceil(timeDomainEnd / tickStepMs) * tickStepMs : null;
  const timeDomainSpan =
    alignedDomainStart !== null && alignedDomainEnd !== null
      ? Math.max(alignedDomainEnd - alignedDomainStart, tickStepMs)
      : null;

  const minPointSpacing = 80;
  const chartMinTickWidth = 180;
  const chartWidth =
    alignedDomainStart !== null && alignedDomainEnd !== null
      ? Math.max(
          800,
          Math.ceil((alignedDomainEnd - alignedDomainStart) / tickStepMs) * chartMinTickWidth + paddingLeft + paddingRight,
          Math.max(0, chartPointsRaw.length - 1) * minPointSpacing + paddingLeft + paddingRight,
        )
      : 800;
  const graphWidth = chartWidth - paddingLeft - paddingRight;
  const graphHeight = 350 - paddingTop - paddingBottom;

  // Default display values if empty
  const hasHistory = chartPointsRaw.length > 0;
  const values = chartPointsRaw.map((p) => p.val);
  let minVal = hasHistory ? Math.min(...values) : 0;
  let maxVal = hasHistory ? Math.max(...values) : 100;

  if (minVal === maxVal) {
    minVal = minVal - 5;
    maxVal = maxVal + 5;
  } else {
    const margin = (maxVal - minVal) * 0.15;
    minVal = minVal - margin;
    maxVal = maxVal + margin;
  }

  // Calculate coordinates mapping for raw history points
  const points = chartPointsRaw.map((p, i) => {
    const timestamp = p.date ? new Date(p.date).getTime() : NaN;
    const timeX =
      alignedDomainStart !== null &&
      timeDomainSpan !== null &&
      Number.isFinite(timestamp) &&
      timeDomainSpan > 0
        ? paddingLeft + ((timestamp - alignedDomainStart) / timeDomainSpan) * graphWidth
        : paddingLeft;
    const indexX = paddingLeft + i * minPointSpacing;
    const x =
      Math.max(
        timeX,
        chartPointsRaw.length > 1 ? indexX : paddingLeft + graphWidth / 2,
      );
    const y = paddingTop + graphHeight - ((p.val - minVal) / (maxVal - minVal)) * graphHeight;
    return { x, y, val: p.val, date: p.date, timestamp: Number.isFinite(timestamp) ? timestamp : null };
  });

  const linePath = points.length > 0 ? getCurvePath(points) : '';
  const fillPath =
    points.length > 0
      ? `${linePath} L ${points[points.length - 1].x} ${paddingTop + graphHeight} L ${points[0].x} ${paddingTop + graphHeight} Z`
      : '';

  // Generate Y scale helper tick lines
  const tickCount = 5;
  const yTicks = Array.from({ length: tickCount }).map((_, i) => {
    const ratio = i / (tickCount - 1);
    const val = minVal + ratio * (maxVal - minVal);
    const y = paddingTop + graphHeight - ratio * graphHeight;
    return { val, y };
  });

  // Generate X scale helper labels (2-hour aligned ticks)
  const xTicks: { label: string; x: number }[] = [];
  if (alignedDomainStart !== null && alignedDomainEnd !== null && timeDomainSpan !== null) {
    for (let tickTime = alignedDomainStart; tickTime <= alignedDomainEnd; tickTime += tickStepMs) {
      const x =
        alignedDomainEnd === alignedDomainStart
          ? paddingLeft + graphWidth / 2
          : paddingLeft + ((tickTime - alignedDomainStart) / timeDomainSpan) * graphWidth;
      xTicks.push({ label: formatTickLabel(new Date(tickTime)), x });
    }
  }

  const handleMouseMove = (e: React.MouseEvent<SVGSVGElement>) => {
    if (points.length === 0) return;
    const rect = e.currentTarget.getBoundingClientRect();
    const mouseX = ((e.clientX - rect.left) / rect.width) * chartWidth;

    let closestIdx = 0;
    let minDiff = Infinity;
    points.forEach((p, idx) => {
      const diff = Math.abs(p.x - mouseX);
      if (diff < minDiff) {
        minDiff = diff;
        closestIdx = idx;
      }
    });

    setHoveredIndex(closestIdx);
  };

  const handleMouseLeave = () => {
    setHoveredIndex(null);
  };

  const activePoint = hoveredIndex !== null ? points[hoveredIndex] : null;

  return (
    <div className="sensor-page flex flex-col gap-5">
      {/* Header section */}
      <section className="rounded-[2rem] border-4 border-bark/10 bg-white/90 p-5 shadow-[0_18px_0_rgba(15,23,42,0.05)]">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <div className="inline-flex rounded-full border-2 border-sky bg-sky/15 px-3 py-1 font-dot text-xs text-sky">
              realtime 센서 보기
            </div>
            <h1 className="mt-3 text-4xl font-black text-bark">센서 놀이터</h1>
            <p className="mt-2 max-w-2xl text-base leading-7 text-bark/70">
              온도, 습도, 조도, 수위, 거리만 보여줘요. 수위는 이제 ADC 원시값 그대로 보여줍니다.
            </p>
          </div>
          <button
            type="button"
            onClick={() => void load()}
            className="rounded-full border-4 border-bark bg-bark px-5 py-3 text-base font-black text-white hover:scale-105 active:scale-95 transition"
          >
            {loading ? '불러오는 중...' : '새로고침'}
          </button>
        </div>

        {error && (
          <div className="mt-4 rounded-[1.2rem] border-4 border-rose-500 bg-rose-500/10 p-4 text-base font-black text-rose-700">
            {error}
          </div>
        )}

        {!error && !hasData && (
          <div className="mt-4 rounded-[1.2rem] border-4 border-amber-400 bg-amber-400/10 p-4 text-base font-black text-amber-800">
            아직 센서 값이 안 들어왔어요. Wemos가 켜져 있는지 확인해 주세요.
          </div>
        )}
      </section>

      {/* Realtime Sensor Value Cards */}
      <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <Card label="상태" value={formatState(realtime?.state_level)} />
        <Card label="온도" value={realtime?.temperature} suffix="°C" />
        <Card label="습도" value={realtime?.humidity} suffix="%" />
        <Card label="조도" value={realtime?.light} suffix="lux" />
      </section>

      <section className="grid gap-4 md:grid-cols-2">
        <Card label="수위(raw)" value={realtime?.water_level} />
        <Card label="거리" value={realtime?.distance} suffix="cm" />
      </section>

      {/* Retro premium Tab based sensor history chart */}
      <section className="rounded-[2rem] border-4 border-bark/10 bg-white/90 p-6 shadow-sm flex flex-col gap-4">
        <div className="flex flex-wrap items-center justify-between gap-3 border-b border-bark/10 pb-4">
          <div>
            <h2 className="text-xl font-pixel text-bark">센서 정밀 분석 리포트</h2>
            <p className="mt-1 font-dot text-xs text-bark/50">최근 24회 측정치의 다이내믹 그라디언트 분석 그래프</p>
          </div>

          {/* Sensor Tabs list */}
          <div className="flex flex-wrap gap-2">
            {(Object.keys(TAB_CONFIGS) as SensorKey[]).map((key) => {
              const active = key === activeTab;
              const cfg = TAB_CONFIGS[key];
              return (
                <button
                  key={key}
                  type="button"
                  onClick={() => {
                    setActiveTab(key);
                    setHoveredIndex(null);
                  }}
                  className={[
                    'rounded-xl border-2 px-3 py-1.5 font-dot text-xs transition duration-200 active:scale-95',
                    active
                      ? `border-[${cfg.stroke}] text-white`
                      : 'border-bark/10 bg-white/50 text-bark/60 hover:border-bark/30 hover:bg-white',
                  ].join(' ')}
                  style={{
                    backgroundColor: active ? cfg.stroke : undefined,
                    borderColor: active ? cfg.stroke : undefined,
                  }}
                >
                  {cfg.label}
                </button>
              );
            })}
          </div>
        </div>

        {/* Dynamic Canvas Chart (SVG) */}
        <div className="relative w-full overflow-x-auto rounded-xl border border-bark/10 bg-[#fcfaf2] p-2">
          {hasHistory ? (
            <svg
              viewBox={`0 0 ${chartWidth} 350`}
              width={chartWidth}
              height={350}
              className="block h-auto select-none"
              onMouseMove={handleMouseMove}
              onMouseLeave={handleMouseLeave}
            >
              <defs>
                <linearGradient id="chart-gradient" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor={activeConfig.stroke} stopOpacity={0.3} />
                  <stop offset="100%" stopColor={activeConfig.stroke} stopOpacity={0} />
                </linearGradient>
              </defs>

              {/* Y Scale Guide Lines */}
              {yTicks.map((tick, i) => (
                <g key={i}>
                  <line
                    x1={paddingLeft}
                    y1={tick.y}
                    x2={chartWidth - paddingRight}
                    y2={tick.y}
                    stroke="rgba(139, 92, 26, 0.08)"
                    strokeDasharray="4 4"
                  />
                  <text
                    x={paddingLeft - 12}
                    y={tick.y + 4}
                    textAnchor="end"
                    className="font-dot text-[10px] fill-bark/60"
                  >
                    {tick.val.toFixed(1)}
                    {activeConfig.suffix}
                  </text>
                </g>
              ))}

              {/* X Scale Guide Labels */}
              {xTicks.map((tick, i) => (
                <g key={i}>
                  <line
                    x1={tick.x}
                    y1={paddingTop + graphHeight}
                    x2={tick.x}
                    y2={paddingTop + graphHeight + 6}
                    stroke="rgba(139, 92, 26, 0.15)"
                  />
                  <text
                    x={tick.x}
                    y={paddingTop + graphHeight + 20}
                    textAnchor="middle"
                    className="font-dot text-[9px] fill-bark/50"
                  >
                    {tick.label}
                  </text>
                </g>
              ))}

              {/* Grid axes */}
              <line
                x1={paddingLeft}
                y1={paddingTop}
                x2={paddingLeft}
                y2={paddingTop + graphHeight}
                stroke="rgba(139, 92, 26, 0.2)"
                strokeWidth="1.5"
              />
              <line
                x1={paddingLeft}
                y1={paddingTop + graphHeight}
                x2={chartWidth - paddingRight}
                y2={paddingTop + graphHeight}
                stroke="rgba(139, 92, 26, 0.2)"
                strokeWidth="1.5"
              />

              {/* Gradient Shading Area */}
              {fillPath && <path d={fillPath} fill="url(#chart-gradient)" />}

              {/* Main Curve Line */}
              {linePath && (
                <path
                  d={linePath}
                  fill="none"
                  stroke={activeConfig.stroke}
                  strokeWidth="3.5"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />
              )}

              {/* Data points (invisible default, interactive hover circles) */}
              {points.map((p, i) => (
                <circle
                  key={i}
                  cx={p.x}
                  cy={p.y}
                  r="3.5"
                  className="transition duration-150"
                  fill={activeConfig.stroke}
                  stroke="#ffffff"
                  strokeWidth="1.5"
                />
              ))}

              {/* Hover Dot & Interactive Tooltip Container */}
              {activePoint && (
                <g>
                  {/* Vertical Tracking Line */}
                  <line
                    x1={activePoint.x}
                    y1={paddingTop}
                    x2={activePoint.x}
                    y2={paddingTop + graphHeight}
                    stroke={activeConfig.stroke}
                    strokeOpacity="0.3"
                    strokeDasharray="3 3"
                  />

                  {/* Pulsing highlight circles */}
                  <circle cx={activePoint.x} cy={activePoint.y} r="9" fill={activeConfig.stroke} fillOpacity="0.2" />
                  <circle cx={activePoint.x} cy={activePoint.y} r="5" fill={activeConfig.stroke} stroke="#ffffff" strokeWidth="2" />

                  {/* Smart Floating Tooltip Box */}
                  <g
                    transform={`translate(${
                      activePoint.x + 15 > 620 ? activePoint.x - 175 : activePoint.x + 15
                    }, ${activePoint.y - 65 < 15 ? activePoint.y + 15 : activePoint.y - 65})`}
                  >
                    <rect
                      width="160"
                      height="58"
                      rx="10"
                      fill="#fcfaf2"
                      stroke="rgba(139, 92, 26, 0.2)"
                      strokeWidth="2.5"
                      style={{ filter: 'drop-shadow(0px 6px 12px rgba(139,92,26,0.08))' }}
                    />
                    <text x="12" y="20" className="font-dot text-[10px] fill-bark/50">
                      {formatTime(activePoint.date)}
                    </text>
                    <text x="12" y="38" className="font-pixel text-[13px] fill-bark">
                      수치:{' '}
                      <tspan fill={activeConfig.stroke} style={{ fontWeight: 'bold' }}>
                        {activePoint.val.toFixed(1)}
                        {activeConfig.suffix}
                      </tspan>
                    </text>
                  </g>
                </g>
              )}
            </svg>
          ) : (
            <div className="flex h-[350px] items-center justify-center font-dot text-sm text-bark/45">
              분석 리포트를 불러올 과거 기록 데이터가 부족합니다.
            </div>
          )}
        </div>
      </section>

      {/* Summary report */}
      <section className="rounded-[1.6rem] border-4 border-bark/10 bg-white/90 p-5">
        <div className="text-xl font-black text-bark">지금 한 줄 요약</div>
        <div className="mt-3 rounded-[1.2rem] border-2 border-bark/10 bg-parchment p-4 font-dot text-sm leading-7 text-bark">
          온도 {realtime?.temperature ?? '-'}°C / 습도 {realtime?.humidity ?? '-'}% / 조도 {realtime?.light ?? '-'} lux /
          수위(raw) {realtime?.water_level ?? '-'} / 거리 {realtime?.distance ?? '-'}cm
        </div>
      </section>
    </div>
  );
}
