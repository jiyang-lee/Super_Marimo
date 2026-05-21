import { type MouseEvent, useMemo, useState } from 'react';
import '../styles/sensor.css';

type SensorKey = 'temperature' | 'humidity' | 'light' | 'water';

type SensorConfig = {
  key: SensorKey;
  label: string;
  unit: string;
  icon: string;
  accent: string;
  base: number;
  range: [number, number];
  step: number;
};

type SensorPoint = {
  date: Date;
  label: string;
  value: number;
};

const SENSOR_STATUS_ITEMS = [
  { label: '온도', value: '24', suffix: '℃', icon: '/images/incoming/icon_temperature.png' },
  { label: '습도', value: '45', suffix: '%', icon: '/images/incoming/icon-humidity.png' },
  { label: '수위', value: '80', suffix: '%', icon: '/images/incoming/icon-water.png' },
  { label: '조도', value: '500', suffix: 'lux', icon: '/images/incoming/icon-light.png' },
] as const;

const SENSOR_CONFIGS: SensorConfig[] = [
  { key: 'temperature', label: '온도', unit: '℃', icon: '/images/incoming/icon_temperature.png', accent: '#e85b50', base: 24.4, range: [22.5, 27.5], step: 0.18 },
  { key: 'humidity', label: '습도', unit: '%', icon: '/images/incoming/icon-humidity.png', accent: '#2f90d1', base: 47.8, range: [40, 60], step: 0.8 },
  { key: 'light', label: '조도', unit: 'lux', icon: '/images/incoming/icon-light.png', accent: '#d38a20', base: 620, range: [380, 1200], step: 26 },
  { key: 'water', label: '수위', unit: '%', icon: '/images/incoming/icon-water.png', accent: '#21a87e', base: 80.4, range: [72, 88], step: 0.32 },
];

function clamp(value: number, min: number, max: number) {
  return Math.max(min, Math.min(value, max));
}

function round1(value: number) {
  return Math.round(value * 10) / 10;
}

function formatDayLabel(date: Date) {
  return `${String(date.getMonth() + 1).padStart(2, '0')}.${String(date.getDate()).padStart(2, '0')}`;
}

function buildLastSevenDays(metric: SensorConfig): SensorPoint[] {
  const today = new Date();
  today.setHours(12, 0, 0, 0);

  return Array.from({ length: 7 }, (_, index) => {
    const date = new Date(today);
    date.setDate(today.getDate() - (6 - index));

    const wave = Math.sin((date.getDate() + metric.step) * 0.72);
    const drift = Math.cos((date.getMonth() + 1 + date.getDate()) * 0.31);
    const rawValue =
      metric.key === 'temperature'
        ? metric.base + wave * 0.7 + drift * 0.3 + index * 0.04
        : metric.key === 'humidity'
          ? metric.base + wave * 2.4 + drift * 1.2 + index * 0.25
          : metric.key === 'light'
            ? metric.base + wave * 90 + drift * 45 + index * 14
            : metric.base + wave * 0.8 + drift * 0.35 + index * 0.06;

    const value = round1(clamp(rawValue, metric.range[0], metric.range[1]));

    return {
      date,
      label: formatDayLabel(date),
      value,
    };
  });
}

function getPointY(value: number, min: number, max: number, height: number, topPadding: number, bottomPadding: number) {
  const plotHeight = height - topPadding - bottomPadding;
  const ratio = (value - min) / (max - min || 1);
  return topPadding + plotHeight - ratio * plotHeight;
}

export function SensorPage() {
  const [selectedSensor, setSelectedSensor] = useState<SensorKey>('temperature');
  const [hoveredIndex, setHoveredIndex] = useState<number | null>(null);

  const selectedConfig = SENSOR_CONFIGS.find((item) => item.key === selectedSensor) ?? SENSOR_CONFIGS[0];
  const history = useMemo(() => buildLastSevenDays(selectedConfig), [selectedConfig]);

  const chartWidth = 980;
  const chartHeight = 391;
  const chartPadding = { top: 24, right: 24, bottom: 54, left: 72 };
  const chartPlotWidth = chartWidth - chartPadding.left - chartPadding.right;
  const chartPlotHeight = chartHeight - chartPadding.top - chartPadding.bottom;
  const stepX = history.length > 1 ? chartPlotWidth / (history.length - 1) : chartPlotWidth;

  const points = history.map((point, index) => ({
    ...point,
    x: chartPadding.left + stepX * index,
    y: getPointY(point.value, selectedConfig.range[0], selectedConfig.range[1], chartHeight, chartPadding.top, chartPadding.bottom),
  }));

  const handleMouseMove = (event: MouseEvent<SVGSVGElement>) => {
    const rect = event.currentTarget.getBoundingClientRect();
    const mouseX = ((event.clientX - rect.left) / rect.width) * chartWidth;

    let closestIndex = 0;
    let closestDistance = Number.POSITIVE_INFINITY;

    points.forEach((point, index) => {
      const distance = Math.abs(point.x - mouseX);
      if (distance < closestDistance) {
        closestDistance = distance;
        closestIndex = index;
      }
    });

    setHoveredIndex(closestIndex);
  };

  return (
    <div className="sensor-page">
      <div className="sensor-page__inner">
        <section className="sensor-panel sensor-panel--status" aria-label="현재 센서 상태">
          <div className="sensor-status-bar" role="list" aria-label="현재 센서 상태 요약">
            {SENSOR_STATUS_ITEMS.map((item) => (
              <div key={item.label} className="sensor-status-item" role="listitem">
                <span className="sensor-status-item__icon" aria-hidden="true">
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

        <section className="sensor-panel sensor-panel--report" aria-label="센서 리포트">
          <div className="sensor-report-frame">
            <div className="sensor-report-frame__inner">
              <div className="sensor-report-hero">
                <div className="sensor-report-copy">
                  <h2 className="sensor-report-copy__title">성장 그래프</h2>
                </div>
              </div>

              <div className="sensor-report-tabs sensor-report-tabs--sensor" role="tablist" aria-label="센서 선택">
                {SENSOR_CONFIGS.map((config) => {
                  const active = selectedSensor === config.key;
                  return (
                    <button
                      key={config.key}
                      type="button"
                      className={`sensor-report-tab sensor-report-tab--sensor ${active ? 'is-active' : ''}`}
                      aria-pressed={active}
                      onClick={() => {
                        setSelectedSensor(config.key);
                        setHoveredIndex(null);
                      }}
                    >
                      <img className="sensor-report-tab__icon" src={config.icon} alt="" aria-hidden="true" />
                      <span className="sensor-report-tab__label">{config.label}</span>
                    </button>
                  );
                })}
              </div>

              <div className="sensor-graph-card">
                <div className="sensor-chart-shell">
                  <svg
                    className="sensor-chart-shell__svg"
                    viewBox={`0 0 ${chartWidth} ${chartHeight}`}
                    role="img"
                    aria-label={`${selectedConfig.label} 최근 7일 그래프`}
                    onMouseMove={handleMouseMove}
                    onMouseLeave={() => setHoveredIndex(null)}
                  >
                    {Array.from({ length: 5 }, (_, index) => {
                      const tick = index * 25;
                      const y = chartPadding.top + chartPlotHeight - (tick / 100) * chartPlotHeight;
                      return (
                        <g key={tick}>
                          <line
                            x1={chartPadding.left}
                            x2={chartWidth - chartPadding.right}
                            y1={y}
                            y2={y}
                            className="sensor-chart-shell__grid-line"
                          />
                          <text x={chartPadding.left - 14} y={y + 4} textAnchor="end" className="sensor-chart-shell__axis-label">
                            {tick}
                          </text>
                        </g>
                      );
                    })}

                    <line
                      x1={chartPadding.left}
                      y1={chartPadding.top}
                      x2={chartPadding.left}
                      y2={chartHeight - chartPadding.bottom}
                      className="sensor-chart-shell__axis"
                    />
                    <line
                      x1={chartPadding.left}
                      y1={chartHeight - chartPadding.bottom}
                      x2={chartWidth - chartPadding.right}
                      y2={chartHeight - chartPadding.bottom}
                      className="sensor-chart-shell__axis"
                    />

                    {points.map((point) => (
                      <text key={point.label} x={point.x} y={chartHeight - 16} textAnchor="middle" className="sensor-chart-shell__week-label">
                        {point.label}
                      </text>
                    ))}

                    {points.length > 1 ? (
                      <path
                        d={points.map((point, index) => `${index === 0 ? 'M' : 'L'} ${point.x} ${point.y}`).join(' ')}
                        fill="none"
                        stroke={selectedConfig.accent}
                        strokeWidth="5.5"
                        strokeLinecap="round"
                        strokeLinejoin="round"
                      />
                    ) : null}

                    {points.map((point, index) => (
                      <g key={point.label}>
                        <circle
                          cx={point.x}
                          cy={point.y}
                          r={hoveredIndex === index ? '7' : '4.5'}
                          fill={selectedConfig.accent}
                          stroke="#fff8e7"
                          strokeWidth="2.4"
                        />
                      </g>
                    ))}

                    {hoveredIndex !== null ? (
                      <g>
                        {(() => {
                          const activePoint = points[hoveredIndex];
                          const tooltipWidth = 176;
                          const tooltipHeight = 68;
                          const tooltipX = activePoint.x + tooltipWidth + 18 > chartWidth ? activePoint.x - tooltipWidth - 18 : activePoint.x + 18;
                          const tooltipY = chartPadding.top + 16;

                          return (
                            <g transform={`translate(${tooltipX}, ${tooltipY})`}>
                              <rect
                                width={tooltipWidth}
                                height={tooltipHeight}
                                rx="14"
                                fill="none"
                                stroke="none"
                              />
                              <text x="88" y="43" textAnchor="middle" className="sensor-chart-tooltip__value">
                                {activePoint.value.toFixed(selectedConfig.key === 'light' ? 0 : 1)}
                                {selectedConfig.unit}
                              </text>
                            </g>
                          );
                        })()}
                      </g>
                    ) : null}
                  </svg>
                </div>
              </div>
            </div>
          </div>
        </section>
      </div>
    </div>
  );
}
