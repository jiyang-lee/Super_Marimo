import { useEffect, useState } from 'react';
import {
  checkAgentHealth,
  checkApiHealth,
  checkLlmHealth,
  checkVoiceHealth,
  listEvents,
  type AgentHealth,
  type ApiHealth,
  type DeviceEvent,
  type LlmHealth,
  type VoiceHealth,
} from '../api';
import { useLiveSensor } from '../contexts/LiveSensorContext';

function StatusDot({ ok }: { ok: boolean }) {
  return <span className={`lab-status-dot ${ok ? 'ok' : 'bad'}`} />;
}

function StatusBadge({ ok, label }: { ok: boolean; label: string }) {
  return (
    <span
      className={[
        'inline-flex rounded-full border-2 px-2 py-0.5 font-dot text-[10px]',
        ok
          ? 'border-grass bg-grass/15 text-grass'
          : 'border-heart-red bg-heart-red/15 text-heart-red',
      ].join(' ')}
    >
      {ok ? 'OK' : 'NG'} {label}
    </span>
  );
}

function formatMetricValue(value: unknown, suffix = '') {
  if (value === null || value === undefined || value === '') return '-';
  return `${value}${suffix}`;
}

export function DashboardPage() {
  const [agent, setAgent] = useState<AgentHealth | null>(null);
  const [api, setApi] = useState<ApiHealth | null>(null);
  const [voice, setVoice] = useState<VoiceHealth | null>(null);
  const [llm, setLlm] = useState<LlmHealth | null>(null);
  const [events, setEvents] = useState<DeviceEvent[]>([]);
  const [error, setError] = useState('');
  const [syncedAt, setSyncedAt] = useState('');
  const { sensor, status: sensorStatus, error: sensorError, syncedAt: sensorSyncedAt, refresh: refreshSensor } =
    useLiveSensor();

  const refresh = async () => {
    setError('');
    try {
      const [nextAgent, nextApi, nextVoice, nextLlm, nextEvents] = await Promise.all([
        checkAgentHealth(),
        checkApiHealth(),
        checkVoiceHealth(),
        checkLlmHealth(),
        listEvents({ limit: 8 }),
      ]);

      setAgent(nextAgent);
      setApi(nextApi);
      setVoice(nextVoice);
      setLlm(nextLlm);
      setEvents(nextEvents.events ?? []);
      setSyncedAt(new Date().toLocaleTimeString('ko-KR'));
      void refreshSensor();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'refresh failed');
    }
  };

  useEffect(() => {
    void refresh();
    const timer = setInterval(() => void refresh(), 10000);
    return () => clearInterval(timer);
  }, []);

  const realtime = sensor?.latest_realtime ?? null;
  const merged = sensor?.latest_merged ?? null;
  const services = [
    { label: 'voice-agent', ok: Boolean(agent?.ok) },
    { label: 'api-server', ok: Boolean(api?.ok) },
    { label: 'voice-server', ok: Boolean(voice?.ok) },
    { label: 'llm-server', ok: Boolean(llm?.ok) },
  ];

  const sensorCards = [
    { label: 'Temperature', value: formatMetricValue(realtime?.temperature ?? merged?.temperature, ' C') },
    { label: 'Humidity', value: formatMetricValue(realtime?.humidity ?? merged?.humidity, '%') },
    {
      label: 'Light',
      value: formatMetricValue(merged?.light_normalized_0_100, '%'),
    },
    {
      label: 'Water',
      value: formatMetricValue(merged?.water_level_normalized_0_100, '%'),
    },
    { label: 'Distance', value: formatMetricValue(realtime?.distance ?? merged?.distance, 'cm') },
    { label: 'Level', value: merged?.state_level ?? 'no data' },
  ];

  const sensorStatusLabel =
    sensorStatus === 'ready' && sensorSyncedAt
      ? `LIVE ${sensorSyncedAt}`
      : sensorStatus === 'loading'
        ? '센서 수신 중'
        : '센서 unavailable';

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="font-pixel text-xl text-grass">운영 콘솔</h1>
          <div className="mt-1 font-pixel text-sm text-bark">현재 서버 상황 / 센서 상황 / 이벤트</div>
        </div>
        <div className="flex items-center gap-2">
          <span className="font-dot text-xs text-bark/60">sync {syncedAt || '...'}</span>
          <span
            className={[
              'font-dot text-xs',
              sensorStatus === 'ready' ? 'text-grass' : sensorStatus === 'error' ? 'text-heart-red' : 'text-bark/60',
            ].join(' ')}
          >
            {sensorStatusLabel}
          </span>
          <button
            onClick={() => void refresh()}
            className="rounded-lg border-2 border-grass bg-grass/10 px-3 py-1 font-dot text-xs text-grass hover:bg-grass/20"
          >
            새로고침
          </button>
        </div>
      </div>

      {error && (
        <div className="rounded-lg border-2 border-heart-red bg-heart-red/10 p-3 font-dot text-sm text-heart-red">
          {error}
        </div>
      )}
      {sensorError && (
        <div className="rounded-lg border-2 border-gold bg-gold/10 p-3 font-dot text-sm text-gold">
          {sensorError}
        </div>
      )}

      {/* Service Health */}
      <div className="pixel-card">
        <h2 className="font-pixel text-sm text-bark">현재 서버 상황</h2>
        <div className="mt-3 grid grid-cols-2 gap-2 sm:grid-cols-4">
          {services.map((svc) => (
            <StatusBadge key={svc.label} ok={svc.ok} label={svc.label} />
          ))}
        </div>
      </div>

      {/* Sensor Snapshot */}
      <div className="pixel-card">
        <h2 className="font-pixel text-sm text-bark">센서 상황</h2>
        <div className="mt-3 grid grid-cols-2 gap-2 sm:grid-cols-3">
          {sensorCards.map((card) => (
            <div key={card.label} className="rounded-lg border border-bark/20 bg-white/60 p-2">
              <div className="font-dot text-[10px] uppercase tracking-wider text-bark/60">{card.label}</div>
              <div className="font-pixel text-sm text-bark">{card.value}</div>
            </div>
          ))}
        </div>
      </div>

      {/* Events */}
      <div className="pixel-card">
        <h2 className="font-pixel text-sm text-bark">이벤트</h2>
        <div className="mt-3 space-y-2">
          {events.length === 0 ? (
            <div className="font-dot text-xs text-bark/50">No events yet.</div>
          ) : (
            events.map((ev) => (
              <div key={ev.event_id} className="rounded-lg border border-bark/15 bg-white/50 p-2">
                <div className="flex items-center justify-between">
                  <span className="font-dot text-[10px] uppercase text-bark/60">{ev.event_type}</span>
                  <span
                    className={['font-dot text-[10px]', ev.played ? 'text-grass' : 'text-gold'].join(' ')}
                  >
                    {ev.status ?? (ev.played ? 'played' : 'pending')}
                  </span>
                </div>
                <div className="mt-1 font-dot text-xs text-bark">{ev.generated_text?.slice(0, 80) || '-'}</div>
                <div className="mt-1 font-dot text-[10px] text-bark/50">
                  {ev.distance ?? '-'}cm · {ev.trigger_source || '-'}
                </div>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
}
