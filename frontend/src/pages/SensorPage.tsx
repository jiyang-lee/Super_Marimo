import { type MouseEvent, useEffect, useMemo, useState } from 'react';
import '../styles/sensor.css';
import { getSensorHistory, type SensorReading } from '../api';
import { useLiveSensor } from '../contexts/LiveSensorContext';

type SensorKey = 'temperature' | 'humidity' | 'light' | 'water';

type SensorConfig = {
  key: SensorKey;
  label: string;
  unit: string;
  icon: string;
  accent: string;
  min: number;
  max: number;
  axisPrecision: number;
  valuePrecision: number;
};

type SensorPoint = {
  date: Date;
  label: string;
  value: number;
};

const HISTORY_LIMIT = 6;
const MAX_POINTS = 6;
const LIGHT_RAW_MIN = 2;
const LIGHT_RAW_MAX = 700;

const SENSOR_CONFIGS: SensorConfig[] = [
  { key: 'temperature', label: '온도', unit: '°C', icon: '/images/incoming/icon_temperature.png', accent: '#e85b50', min: 0, max: 40, axisPrecision: 0, valuePrecision: 1 },
  { key: 'humidity', label: '습도', unit: '%', icon: '/images/incoming/icon-humidity.png', accent: '#2f90d1', min: 0, max: 100, axisPrecision: 0, valuePrecision: 0 },
  { key: 'water', label: '수위', unit: '%', icon: '/images/incoming/icon-water.png', accent: '#21a87e', min: 0, max: 100, axisPrecision: 0, valuePrecision: 0 },
  { key: 'light', label: '조도', unit: '%', icon: '/images/incoming/icon-light.png', accent: '#d38a20', min: 0, max: 100, axisPrecision: 0, valuePrecision: 0 },
];

function clamp(value: number, min: number, max: number): number {
  return Math.min(max, Math.max(min, value));
}

function pad(value: number): string {
  return String(value).padStart(2, '0');
}

function formatHourLabel(date: Date): string {
  return `${pad(date.getHours())}:00`;
}

function normalizeLightPercent(light: number | null | undefined): number | null {
  if (light === null || light === undefined || Number.isNaN(light)) return null;
  const normalized = Math.round(((light - LIGHT_RAW_MIN) / (LIGHT_RAW_MAX - LIGHT_RAW_MIN)) * 100);
  return clamp(normalized, 0, 100);
}

function getSensorValue(reading: SensorReading, key: SensorKey): number | null {
  switch (key) {
    case 'temperature':
      return reading.temperature ?? null;
    case 'humidity':
      return reading.humidity ?? null;
    case 'water':
      return reading.water_level_normalized_0_100 ?? reading.water_level ?? null;
    case 'light':
      return reading.light_normalized_0_100 ?? normalizeLightPercent(reading.light);
    default:
      return null;
  }
}

function buildHourlyPoints(rows: SensorReading[], key: SensorKey, config: SensorConfig): SensorPoint[] {
  const byHour = new Map<string, SensorPoint>();

  [...rows]
    .filter((row) => Boolean(row.created_at))
    .sort((left, right) => {
      const leftTime = new Date(left.created_at ?? '').getTime();
      const rightTime = new Date(right.created_at ?? '').getTime();
      return leftTime - rightTime;
    })
    .forEach((row) => {
      const createdAt = row.created_at ? new Date(row.created_at) : null;
      if (!createdAt || Number.isNaN(createdAt.getTime())) return;

      const value = getSensorValue(row, key);
      if (value === null || value === undefined || Number.isNaN(value)) return;

      const hour = new Date(createdAt);
      hour.setMinutes(0, 0, 0);
      const hourKey = `${hour.getFullYear()}-${pad(hour.getMonth() + 1)}-${pad(hour.getDate())}-${pad(hour.getHours())}`;

      byHour.set(hourKey, {
        date: hour,
        label: formatHourLabel(hour),
        value: clamp(value, config.min, config.max),
      });
    });

  return Array.from(byHour.values())
    .sort((left, right) => left.date.getTime() - right.date.getTime())
    .slice(-MAX_POINTS);
}

function formatStatusValue(value: number | null | undefined, precision = 0): string {
  if (value === null || value === undefined || Number.isNaN(value)) return '-';
  return value.toFixed(precision);
}

function getLatestDisplayValue(value: number | null | undefined): string {
  if (value === null || value === undefined || Number.isNaN(value)) return '-';
  return String(Math.round(value));
}

export function SensorPage() {
  const [selectedSensor, setSelectedSensor] = useState<SensorKey>('temperature');
  const [hoveredIndex, setHoveredIndex] = useState<number | null>(null);
  const [hourlyHistory, setHourlyHistory] = useState<SensorReading[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const { sensor, status: sensorStatus, error: sensorError, syncedAt: sensorSyncedAt } = useLiveSensor();

  const realtime = sensor?.latest_realtime;
  const merged = sensor?.latest_merged;

  const selectedConfig = SENSOR_CONFIGS.find((item) => item.key === selectedSensor) ?? SENSOR_CONFIGS[0];
  const hourlyRows = hourlyHistory;

  const sensorStatusItems = useMemo(() => {
    const lightPercent = merged?.light_normalized_0_100 ?? normalizeLightPercent(merged?.light);
    const waterPercent = merged?.water_level_normalized_0_100 ?? merged?.water_level;

    return [
      { label: '온도', value: formatStatusValue(realtime?.temperature ?? merged?.temperature, 1), suffix: '°C', icon: '/images/incoming/icon_temperature.png' },
      { label: '습도', value: getLatestDisplayValue(realtime?.humidity ?? merged?.humidity), suffix: '%', icon: '/images/incoming/icon-humidity.png' },
      { label: '수위', value: getLatestDisplayValue(waterPercent), suffix: '%', icon: '/images/incoming/icon-water.png' },
      { label: '조도', value: getLatestDisplayValue(lightPercent), suffix: '%', icon: '/images/incoming/icon-light.png' },
    ];
  }, [merged, realtime]);

  const chartPoints = useMemo(
    () => buildHourlyPoints(hourlyRows, selectedSensor, selectedConfig),
    [hourlyRows, selectedConfig, selectedSensor],
  );

  const load = async () => {
    setLoading(true);
    setError('');
    try {
      const historyResult = await getSensorHistory(HISTORY_LIMIT);
      setHourlyHistory(historyResult.hourly_history ?? []);
    } catch (e) {
      setError(e instanceof Error ? e.message : '센서 데이터를 불러오지 못했습니다.');
    } finally {
      setLoading(false);
    }
  };

  const silentLoad = async () => {
    try {
      const historyResult = await getSensorHistory(HISTORY_LIMIT);
      setHourlyHistory(historyResult.hourly_history ?? []);
    } catch {
      // silent fail
    }
  };

  useEffect(() => {
    void load();
    const timer = setInterval(() => void silentLoad(), 60000);
    return () => clearInterval(timer);
  }, []);

  const chartWidth = 980;
  const chartHeight = 391;
  const chartPadding = { top: 24, right: 24, bottom: 60, left: 72 };
  const chartPlotWidth = chartWidth - chartPadding.left - chartPadding.right;
  const chartPlotHeight = chartHeight - chartPadding.top - chartPadding.bottom;
  
  const latestTime = chartPoints.length > 0 ? chartPoints[chartPoints.length - 1].date.getTime() : new Date().getTime();
  const latestHour = new Date(latestTime);
  latestHour.setMinutes(0, 0, 0, 0);

  const axisHours = Array.from({ length: MAX_POINTS }, (_, i) => {
    const d = new Date(latestHour.getTime() - (MAX_POINTS - 1 - i) * 60 * 60 * 1000);
    return { date: d, label: formatHourLabel(d), x: chartPadding.left + (chartPlotWidth / (MAX_POINTS - 1)) * i };
  });

  const minTime = axisHours[0].date.getTime();
  const maxTime = axisHours[MAX_POINTS - 1].date.getTime();

  const points = chartPoints
    .filter(p => p.date.getTime() >= minTime && p.date.getTime() <= maxTime)
    .map((point) => {
      const hourDiff = (point.date.getTime() - minTime) / (60 * 60 * 1000);
      return {
        ...point,
        x: chartPadding.left + (chartPlotWidth / (MAX_POINTS - 1)) * hourDiff,
        y: chartPadding.top + chartPlotHeight - ((point.value - selectedConfig.min) / (selectedConfig.max - selectedConfig.min || 1)) * chartPlotHeight,
      };
    });

  const handleMouseMove = (event: MouseEvent<SVGSVGElement>) => {
    if (points.length === 0) return;

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

  const axisSteps = Array.from({ length: 5 }, (_, index) => selectedConfig.min + ((selectedConfig.max - selectedConfig.min) * index) / 4);

  return (
    <div className="sensor-page">
      <div className="sensor-page__inner">
        <section className="sensor-panel sensor-panel--status" aria-label="현재 센서 상태">
          <div className="sensor-status-bar" role="list" aria-label="현재 센서 상태 요약">
            {sensorStatusItems.map((item) => (
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
                  <div className="sensor-report-copy__subtitle">
                    {selectedConfig.label} 데이터를 시간별 기록으로 그립니다. 시간별 기록이 없으면 실시간 데이터를 집계해 표시합니다. 최근 6시간, 오른쪽이 최신입니다.
                  </div>
                  {sensorStatus === 'ready' && sensorSyncedAt && (
                    <div className="sensor-report-copy__badge">센서 LIVE {sensorSyncedAt}</div>
                  )}
                  {sensorStatus === 'loading' && <div className="sensor-report-copy__badge">센서 갱신 중</div>}
                  {sensorError && <div className="sensor-report-copy__badge sensor-report-copy__badge--error">{sensorError}</div>}
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
                  {loading && (
                    <div className="sensor-chart-shell__loading">
                      <div className="sensor-chart-shell__loading-text">데이터를 불러오는 중입니다...</div>
                    </div>
                  )}

                  {error && (
                    <div className="sensor-chart-shell__error">
                      <div className="sensor-chart-shell__error-text">{error}</div>
                    </div>
                  )}

                  {!loading && !error && (
                    <svg
                      className="sensor-chart-shell__svg"
                      viewBox={`0 0 ${chartWidth} ${chartHeight}`}
                      role="img"
                      aria-label={`${selectedConfig.label} 최근 6시간 그래프`}
                      onMouseMove={handleMouseMove}
                      onMouseLeave={() => setHoveredIndex(null)}
                    >
                      {axisSteps.map((tick, index) => {
                        const y = chartPadding.top + chartPlotHeight - (index / 4) * chartPlotHeight;
                        return (
                          <g key={`${selectedSensor}-${tick}`}>
                            <line
                              x1={chartPadding.left}
                              x2={chartWidth - chartPadding.right}
                              y1={y}
                              y2={y}
                              className="sensor-chart-shell__grid-line"
                            />
                            <text x={chartPadding.left - 14} y={y + 4} textAnchor="end" className="sensor-chart-shell__axis-label">
                              {tick.toFixed(selectedConfig.axisPrecision)}
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

                      {axisHours.map((hourObj) => (
                        <text key={`label-${hourObj.label}`} x={hourObj.x} y={chartHeight - 16} textAnchor="middle" className="sensor-chart-shell__hour-label">
                          {hourObj.label}
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
                        <g key={`${point.label}-${point.date.toISOString()}-dot`}>
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

                      {hoveredIndex !== null && points[hoveredIndex] ? (
                        <g>
                          {(() => {
                            const activePoint = points[hoveredIndex];
                            const tooltipWidth = 176;
                            const tooltipHeight = 68;
                            const tooltipX = activePoint.x + tooltipWidth + 18 > chartWidth ? activePoint.x - tooltipWidth - 18 : activePoint.x + 18;
                            const tooltipY = activePoint.y - tooltipHeight - 16 < 0 ? activePoint.y + 20 : activePoint.y - tooltipHeight - 16;

                            return (
                              <>
                                <line
                                  x1={activePoint.x}
                                  x2={activePoint.x}
                                  y1={chartPadding.top}
                                  y2={chartHeight - chartPadding.bottom}
                                  stroke="rgba(126,98,56,0.25)"
                                  strokeWidth="1"
                                  strokeDasharray="4 4"
                                />
                                <g transform={`translate(${tooltipX}, ${tooltipY})`}>
                                  <rect
                                    width={tooltipWidth}
                                    height={tooltipHeight}
                                    rx="12"
                                    fill="rgba(255,250,240,0.95)"
                                    stroke="rgba(139,94,36,0.2)"
                                    strokeWidth="1"
                                    style={{ filter: 'drop-shadow(0 4px 12px rgba(0,0,0,0.08))' }}
                                  />
                                  <text x="88" y="25" textAnchor="middle" className="sensor-chart-tooltip__title">
                                    {activePoint.label}
                                  </text>
                                  <text x="88" y="52" textAnchor="middle" className="sensor-chart-tooltip__value">
                                    {activePoint.value.toFixed(selectedConfig.valuePrecision)}
                                    {selectedConfig.unit}
                                  </text>
                                </g>
                              </>
                            );
                          })()}
                        </g>
                      ) : null}
                    </svg>
                  )}
                </div>
              </div>
            </div>
          </div>
        </section>
      </div>
    </div>
  );
}
