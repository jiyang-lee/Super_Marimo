import { useEffect, useState } from 'react';
import {
  checkAgentHealth,
  checkApiHealth,
  checkLlmHealth,
  checkVoiceHealth,
  getLatestSensor,
  listEvents,
  type AgentHealth,
  type ApiHealth,
  type DeviceEvent,
  type LlmHealth,
  type SensorLatest,
  type VoiceHealth,
} from '../api';

function StatusDot({ ok }: { ok: boolean }) {
  return <span className={`lab-status-dot ${ok ? 'ok' : 'bad'}`} />;
}

function formatMetricValue(value: unknown, suffix = '') {
  if (value === null || value === undefined || value === '') return '-';
  return `${value}${suffix}`;
}

function formatNormalizedWithRaw(normalized: unknown, raw: unknown, suffix = '') {
  const normalizedText = formatMetricValue(normalized, suffix);
  const rawText = formatMetricValue(raw);
  if (rawText === '-') {
    return normalizedText;
  }
  return `${normalizedText} (raw ${rawText})`;
}

function normalizeToPercent(value: unknown, reference: unknown) {
  const current = Number(value);
  const base = Number(reference);
  if (!Number.isFinite(current) || !Number.isFinite(base) || base <= 0) return null;
  const normalized = Math.round((current / base) * 100);
  return Math.max(0, Math.min(100, normalized));
}

function normalizeLightRange(value: unknown) {
  const current = Number(value);
  if (!Number.isFinite(current)) return null;
  const normalized = Math.round(((current - 2) / (700 - 2)) * 100);
  return Math.max(0, Math.min(100, normalized));
}

export function DashboardPage() {
  const [agent, setAgent] = useState<AgentHealth | null>(null);
  const [api, setApi] = useState<ApiHealth | null>(null);
  const [voice, setVoice] = useState<VoiceHealth | null>(null);
  const [llm, setLlm] = useState<LlmHealth | null>(null);
  const [sensor, setSensor] = useState<SensorLatest | null>(null);
  const [events, setEvents] = useState<DeviceEvent[]>([]);
  const [error, setError] = useState('');
  const [syncedAt, setSyncedAt] = useState('');

  const refresh = async () => {
    setError('');
    try {
      const [nextAgent, nextApi, nextVoice, nextLlm, nextSensor, nextEvents] = await Promise.all([
        checkAgentHealth(),
        checkApiHealth(),
        checkVoiceHealth(),
        checkLlmHealth(),
        getLatestSensor(),
        listEvents({ limit: 8 }),
      ]);

      setAgent(nextAgent);
      setApi(nextApi);
      setVoice(nextVoice);
      setLlm(nextLlm);
      setSensor(nextSensor);
      setEvents(nextEvents.events ?? []);
      setSyncedAt(new Date().toLocaleTimeString('ko-KR'));
    } catch (e) {
      setError(e instanceof Error ? e.message : 'refresh failed');
    }
  };

  useEffect(() => {
    void refresh();
    const timer = setInterval(() => void refresh(), 10000);
    return () => clearInterval(timer);
  }, []);

  const merged = sensor?.latest_merged ?? null;
  const services = [
    { label: 'voice-agent', ok: Boolean(agent?.ok) },
    { label: 'api-server', ok: Boolean(api?.ok) },
    { label: 'voice-server', ok: Boolean(voice?.ok) },
    { label: 'llm-server', ok: Boolean(llm?.ok) },
  ];

  const sensorCards = [
    { label: 'Temperature', value: formatMetricValue(merged?.temperature, ' C') },
    { label: 'Humidity', value: formatMetricValue(merged?.humidity, '%') },
    {
      label: 'Light',
      value: formatNormalizedWithRaw(
        merged?.light_normalized_0_100 ?? normalizeLightRange(merged?.light),
        merged?.light,
      ),
    },
    {
      label: 'Water',
      value: formatNormalizedWithRaw(
        merged?.water_level_normalized_0_100 ?? normalizeToPercent(merged?.water_level, merged?.water_level_recent_avg_2h),
        merged?.water_level,
      ),
    },
    { label: 'Distance', value: formatMetricValue(merged?.distance, 'cm') },
    { label: 'Level', value: merged?.state_level ?? 'no data' },
  ];

  return (
    <div className="lab-stack">
      <div className="lab-flex-between">
        <div>
          <span className="lab-pill">운영 콘솔</span>
          <div style={{ marginTop: 8, fontSize: 18, fontWeight: 900, color: '#355338' }}>
            현재 서버 상황 / 센서 상황 / 이벤트
          </div>
        </div>
        <div className="lab-flex-wrap">
          <span style={{ fontSize: 12, color: '#667085', fontFamily: '"Cascadia Mono", "SFMono-Regular", Consolas, monospace' }}>
            sync {syncedAt || '...'}
          </span>
          <button className="lab-btn lab-btn-secondary" onClick={() => void refresh()}>
            새로고침
          </button>
        </div>
      </div>

      {error && <div className="lab-log-item bad">{error}</div>}

      <div className="lab-sub-panel">
        <div className="lab-sub-panel-head">
          <h2>현재 서버 상황</h2>
        </div>
        <div className="lab-sub-panel-body">
          <div className="lab-status-strip">
            {services.map((svc) => (
              <div key={svc.label} className="lab-status-card">
                <div className="lab-status-name">
                  {svc.label}
                  <StatusDot ok={svc.ok} />
                </div>
                <div className="lab-status-value">{svc.ok ? 'OK' : 'NG'}</div>
              </div>
            ))}
          </div>
        </div>
      </div>

      <div className="lab-sub-panel">
        <div className="lab-sub-panel-head">
          <h2>센서 상황</h2>
        </div>
        <div className="lab-sub-panel-body">
          <div className="lab-grid-3">
            {sensorCards.map((card) => (
              <div key={card.label} className="lab-card lab-card-column">
                <div className="lab-card-label">{card.label}</div>
                <div className="lab-card-value">{card.value}</div>
              </div>
            ))}
          </div>
        </div>
      </div>

      <div className="lab-sub-panel">
        <div className="lab-sub-panel-head">
          <h2>이벤트</h2>
        </div>
        <div className="lab-sub-panel-body">
          {events.length === 0 ? (
            <div style={{ fontSize: 13, color: '#667085' }}>No events yet.</div>
          ) : (
            <div className="lab-log-list">
              {events.map((ev) => (
                <div key={ev.event_id} className={`lab-log-item ${ev.played ? 'ok' : 'warn'}`}>
                  <div className="lab-flex-between" style={{ width: '100%' }}>
                    <span className="lab-log-time">{ev.event_type}</span>
                    <span className={`lab-pill ${ev.played ? 'lab-pill-ok' : 'lab-pill-warn'}`}>
                      {ev.status ?? (ev.played ? 'played' : 'pending')}
                    </span>
                  </div>
                  <div style={{ marginTop: 6, color: '#1f2937', fontSize: 13 }}>
                    {ev.generated_text?.slice(0, 80) || '-'}
                  </div>
                  <div style={{ marginTop: 4, fontSize: 12, color: '#667085' }}>
                    {ev.distance ?? '-'}cm · {ev.trigger_source || '-'}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
