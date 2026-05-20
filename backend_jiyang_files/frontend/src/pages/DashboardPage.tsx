import { useEffect, useState } from 'react';
import {
  checkAgentHealth,
  checkApiHealth,
  checkLlmHealth,
  checkVoiceHealth,
  getLatestSensor,
  listEvents,
  listSessions,
  type AgentHealth,
  type ApiHealth,
  type LlmHealth,
  type SensorLatest,
  type SessionSummary,
  type VoiceHealth,
} from '../api';

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

export function DashboardPage() {
  const [agent, setAgent] = useState<AgentHealth | null>(null);
  const [api, setApi] = useState<ApiHealth | null>(null);
  const [voice, setVoice] = useState<VoiceHealth | null>(null);
  const [llm, setLlm] = useState<LlmHealth | null>(null);
  const [sensor, setSensor] = useState<SensorLatest | null>(null);
  const [sessions, setSessions] = useState<SessionSummary[]>([]);
  const [events, setEvents] = useState<any[]>([]);
  const [error, setError] = useState('');
  const [syncedAt, setSyncedAt] = useState('');

  const refresh = async () => {
    setError('');
    try {
      const [a, b, c, d, s, ses, ev] = await Promise.all([
        checkAgentHealth(),
        checkApiHealth(),
        checkVoiceHealth(),
        checkLlmHealth(),
        getLatestSensor(),
        listSessions(5),
        listEvents({ limit: 5 }),
      ]);
      setAgent(a);
      setApi(b);
      setVoice(c);
      setLlm(d);
      setSensor(s);
      setSessions(ses);
      setEvents(ev.events ?? []);
      setSyncedAt(new Date().toLocaleTimeString('ko-KR'));
    } catch (e) {
      setError(e instanceof Error ? e.message : 'refresh failed');
    }
  };

  useEffect(() => {
    void refresh();
    const t = setInterval(() => void refresh(), 10000);
    return () => clearInterval(t);
  }, []);

  const merged = sensor?.latest_merged ?? null;
  const runtimeSettings = sensor?.runtime_settings ?? null;
  const latestEvent = events[0] ?? null;

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center justify-between">
        <h1 className="font-pixel text-xl text-grass">Dashboard</h1>
        <div className="flex items-center gap-2">
          <span className="font-dot text-xs text-bark/60">sync {syncedAt || '...'}</span>
          <button
            onClick={() => void refresh()}
            className="rounded-lg border-2 border-grass bg-grass/10 px-3 py-1 font-dot text-xs text-grass hover:bg-grass/20"
          >
            refresh
          </button>
        </div>
      </div>

      {error && (
        <div className="rounded-lg border-2 border-heart-red bg-heart-red/10 p-3 font-dot text-sm text-heart-red">
          {error}
        </div>
      )}

      {/* Service Health */}
      <div className="pixel-card">
        <h2 className="font-pixel text-sm text-bark">Service Health</h2>
        <div className="mt-3 grid grid-cols-2 gap-2 sm:grid-cols-4">
          <StatusBadge ok={Boolean(agent?.ok)} label="voice-agent" />
          <StatusBadge ok={Boolean(api?.ok)} label="api-server" />
          <StatusBadge ok={Boolean(voice?.ok)} label="voice-server" />
          <StatusBadge ok={Boolean(llm?.ok)} label="llm-server" />
        </div>
      </div>

      {/* Sensor Snapshot */}
      <div className="pixel-card">
        <h2 className="font-pixel text-sm text-bark">Sensor Snapshot</h2>
        <div className="mt-3 grid grid-cols-2 gap-2 sm:grid-cols-3">
          {[
            { label: 'Temperature', value: merged?.temperature ?? '-', suffix: '°C' },
            { label: 'Humidity', value: merged?.humidity ?? '-', suffix: '%' },
            { label: 'Light', value: merged?.light ?? '-', suffix: '' },
            { label: 'Water(raw)', value: merged?.water_level ?? '-', suffix: '' },
            { label: 'Distance', value: merged?.distance ?? '-', suffix: 'cm' },
            { label: 'Level', value: merged?.state_level ?? 'no data', suffix: '' },
          ].map((s) => (
            <div key={s.label} className="rounded-lg border border-bark/20 bg-white/60 p-2">
              <div className="font-dot text-[10px] uppercase tracking-wider text-bark/60">{s.label}</div>
              <div className="font-pixel text-sm text-bark">
                {s.value}
                {s.suffix}
              </div>
            </div>
          ))}
        </div>
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <div className="pixel-card">
          <h2 className="font-pixel text-sm text-bark">Runtime Settings</h2>
          <div className="mt-3 grid grid-cols-2 gap-2 sm:grid-cols-4">
            {[
              { label: 'wake', value: runtimeSettings?.wake_enabled ? 'ON' : 'OFF' },
              { label: 'distance', value: runtimeSettings?.distance_detection_enabled ? 'ON' : 'OFF' },
              { label: 'web voice', value: runtimeSettings?.web_voice_enabled ? 'ON' : 'OFF' },
              { label: 'threshold', value: `${runtimeSettings?.distance_threshold_cm ?? '-'} cm` },
            ].map((item) => (
              <div key={item.label} className="rounded-lg border border-bark/20 bg-white/60 p-2">
                <div className="font-dot text-[10px] uppercase tracking-wider text-bark/60">{item.label}</div>
                <div className="font-pixel text-sm text-bark">{item.value}</div>
              </div>
            ))}
          </div>
        </div>

        <div className="pixel-card">
          <h2 className="font-pixel text-sm text-bark">Latest Action</h2>
          {latestEvent ? (
            <div className="mt-3 rounded-lg border border-bark/15 bg-white/60 p-3">
              <div className="flex items-center justify-between gap-2">
                <span className="font-dot text-[10px] uppercase text-bark/60">{latestEvent.event_type}</span>
                <span className={['font-dot text-[10px]', latestEvent.played ? 'text-grass' : 'text-gold'].join(' ')}>
                  {latestEvent.status ?? (latestEvent.played ? 'played' : 'pending')}
                </span>
              </div>
              <div className="mt-2 font-dot text-xs text-bark">{latestEvent.generated_text?.slice(0, 80) || '-'}</div>
              <div className="mt-1 font-dot text-[10px] text-bark/50">
                {latestEvent.distance ?? '-'}cm · {latestEvent.trigger_source || '-'}
              </div>
            </div>
          ) : (
            <div className="mt-3 font-dot text-xs text-bark/50">No recent action yet.</div>
          )}
        </div>
      </div>

      {/* Recent Events */}
      <div className="pixel-card">
        <h2 className="font-pixel text-sm text-bark">Recent Events</h2>
        <div className="mt-3 space-y-2">
          {events.length === 0 && (
            <div className="font-dot text-xs text-bark/50">No events yet.</div>
          )}
          {events.map((ev: any) => (
            <div
              key={ev.event_id}
              className="flex items-center justify-between rounded-lg border border-bark/15 bg-white/50 p-2"
            >
              <div className="flex items-center gap-2">
                <span className="font-dot text-[10px] uppercase text-bark/60">{ev.event_type}</span>
                <span className="font-dot text-xs text-bark">{ev.generated_text?.slice(0, 30) || '-'}</span>
              </div>
              <span className={['font-dot text-[10px]', ev.played ? 'text-grass' : 'text-gold'].join(' ')}>
                {ev.status ?? (ev.played ? 'played' : 'pending')}
              </span>
            </div>
          ))}
        </div>
      </div>

      {/* Recent Sessions */}
      <div className="pixel-card">
        <h2 className="font-pixel text-sm text-bark">Recent Sessions</h2>
        <div className="mt-3 space-y-2">
          {sessions.length === 0 && (
            <div className="font-dot text-xs text-bark/50">No sessions yet.</div>
          )}
          {sessions.map((ses) => (
            <div
              key={ses.session_id}
              className="flex items-center justify-between rounded-lg border border-bark/15 bg-white/50 p-2"
            >
              <div>
                <div className="font-dot text-xs text-bark">{ses.title || 'New chat'}</div>
                <div className="font-dot text-[10px] text-bark/60">{ses.preview?.slice(0, 40)}</div>
              </div>
              <span className={['font-dot text-[10px]', ses.ended_at ? 'text-bark/40' : 'text-grass'].join(' ')}>
                {ses.ended_at ? 'ended' : 'live'}
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
