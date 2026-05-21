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
  base: number;
  range: [number, number];
  step: number;
};

type SensorPoint = {
  date: Date;
  label: string;
  value: number;
};

const SENSOR_CONFIGS: SensorConfig[] = [
  { key: 'temperature', label: '온도', unit: '℃', icon: '/images/incoming/icon_temperature.png', accent: '#e85b50', base: 24.4, range: [22.5, 27.5], step: 0.18 },
  { key: 'humidity', label: '습도', unit: '%', icon: '/images/incoming/icon-humidity.png', accent: '#2f90d1', base: 47.8, range: [40, 60], step: 0.8 },
  { key: 'light', label: '조도', unit: 'lux', icon: '/images/incoming/icon-light.png', accent: '#d38a20', base: 620, range: [380, 1200], step: 26 },
  { key: 'water', label: '수위', unit: '%', icon: '/images/incoming/icon-water.png', accent: '#21a87e', base: 80.4, range: [72, 88], step: 0.32 },
];

function formatValue(value: number | null | undefined, fallback = '-'): string {
  if (value === null || value === undefined) return fallback;
  return String(value);
}

function formatDayLabel(date: Date) {
  return `${String(date.getMonth() + 1).padStart(2, '0')}.${String(date.getDate()).padStart(2, '0')}`;
}

function getPointY(value: number, min: number, max: number, height: number, topPadding: number, bottomPadding: number) {
  const plotHeight = height - topPadding - bottomPadding;
  const ratio = (value - min) / (max - min || 1);
  return topPadding + plotHeight - ratio * plotHeight;
}

function mapHistoryToPoints(history: SensorReading[], key: SensorKey): SensorPoint[] {
  const fieldMap: Record<SensorKey, keyof SensorReading> = {
    temperature: 'temperature',
    humidity: 'humidity',
    light: 'light',
    water: 'water_level',
  };
  const field = fieldMap[key];

  // 최근 7개만 사용 (team-a UI가 7개 포인트 기반)
  const recent = history.slice(-7);

  return recent
    .map((item) => {
      const val = item[field] as number | undefined;
      if (val === undefined || val === null) return null;
      const date = item.created_at ? new Date(item.created_at) : new Date();
      return {
        date,
        label: formatDayLabel(date),
        value: val,
      };
    })
    .filter((p): p is SensorPoint => p !== null);
}

export function SensorPage() {
  const [selectedSensor, setSelectedSensor] = useState<SensorKey>('temperature');
  const [hoveredIndex, setHoveredIndex] = useState<number | null>(null);
  const [history, setHistory] = useState<SensorReading[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const { sensor, status: sensorStatus, error: sensorError, syncedAt: sensorSyncedAt } = useLiveSensor();

  const realtime = sensor?.latest_realtime;
  const merged = sensor?.latest_merged;

  const sensorStatusItems = useMemo(() => {
    const getVal = (realtimeVal: number | undefined, mergedVal: number | undefined, fallback = '-') => {
      const v = realtimeVal ?? mergedVal;
      return v !== undefined && v !== null ? String(v) : fallback;
    };
    return [
      { label: '온도', value: getVal(realtime?.temperature, merged?.temperature), suffix: '℃', icon: '/images/incoming/icon_temperature.png' },
      { label: '습도', value: getVal(realtime?.humidity, merged?.humidity), suffix: '%', icon: '/images/incoming/icon-humidity.png' },
      { label: '수위', value: getVal(merged?.water_level_normalized_0_100, merged?.water_level), suffix: '%', icon: '/images/incoming/icon-water.png' },
      { label: '조도', value: getVal(merged?.light_normalized_0_100, merged?.light), suffix: 'lux', icon: '/images/incoming/icon-light.png' },
    ];
  }, [realtime, merged]);

  const load = async () => {
    setLoading(true);
    setError('');
    try {
      const historyResult = await getSensorHistory(120);
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

  const selectedConfig = SENSOR_CONFIGS.find((item) => item.key === selectedSensor) ?? SENSOR_CONFIGS[0];
  const chartPoints = useMemo(() => mapHistoryToPoints(history, selectedSensor), [history, selectedSensor]);

  // 실제 데이터 기반 range 계산 (데이터 없으면 config 기본값 사용)
  const dataValues = chartPoints.map((p) => p.value);
  const dataMin = dataValues.length > 0 ? Math.min(...dataValues) : selectedConfig.range[0];
  const dataMax = dataValues.length > 0 ? Math.max(...dataValues) : selectedConfig.range[1];
  // 여유 공간 추가
  const rangeMin = dataMin - (dataMax - dataMin) * 0.1;
  const rangeMax = dataMax + (dataMax - dataMin) * 0.1;

  const chartWidth = 980;
  const chartHeight = 391;
  const chartPadding = { top: 24, right: 24, bottom: 54, left: 72 };
  const chartPlotWidth = chartWidth - chartPadding.left - chartPadding.right;
  const chartPlotHeight = chartHeight - chartPadding.top - chartPadding.bottom;
  const stepX = chartPoints.length > 1 ? chartPlotWidth / (chartPoints.length - 1) : chartPlotWidth;

  const points = chartPoints.map((point, index) => ({
    ...point,
    x: chartPadding.left + stepX * index,
    y: getPointY(point.value, rangeMin, rangeMax, chartHeight, chartPadding.top, chartPadding.bottom),
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
                  {sensorStatus === 'ready' && sensorSyncedAt && (
                    <div className="sensor-report-copy__badge">센서 LIVE {sensorSyncedAt}</div>
                  )}
                  {sensorStatus === 'loading' && (
                    <div className="sensor-report-copy__badge">센서 수신 중</div>
                  )}
                  {sensorError && (
                    <div className="sensor-report-copy__badge sensor-report-copy__badge--error">{sensorError}</div>
                  )}
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
                      <div className="sensor-chart-shell__loading-text">데이터를 불러오는 중...</div>
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
                      aria-label={`${selectedConfig.label} 최근 측정 그래프`}
                      onMouseMove={handleMouseMove}
                      onMouseLeave={() => setHoveredIndex(null)}
                    >
                      {Array.from({ length: 5 }, (_, index) => {
                        const tick = rangeMin + ((rangeMax - rangeMin) * index) / 4;
                        const y = chartPadding.top + chartPlotHeight - (index / 4) * chartPlotHeight;
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
                              {Number(tick.toFixed(1))}
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
