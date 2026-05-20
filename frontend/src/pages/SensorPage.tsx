import { useEffect, useState } from 'react';
import {
  getLatestSensor,
  getSensorHistory,
  getWaterRawSamples,
  ingestRealtimeSensor,
  listEvents,
  updateRuntimeSettings,
  type DeviceEvent,
  type RuntimeSettings,
  type SensorReading,
  type WaterRawSample,
} from '../api';

function Metric({ label, value, suffix }: { label: string; value: string | number | null | undefined; suffix?: string }) {
  const text = value === null || value === undefined || value === '' ? '-' : `${value}${suffix ?? ''}`;
  return (
    <div className="sensor-card">
      <span className="font-dot text-[10px] uppercase tracking-wider text-bark/60">{label}</span>
      <span className="font-pixel text-lg text-bark">{text}</span>
    </div>
  );
}

function Toggle({
  label,
  checked,
  onChange,
}: {
  label: string;
  checked: boolean;
  onChange: (next: boolean) => void;
}) {
  return (
    <button
      type="button"
      onClick={() => onChange(!checked)}
      className={[
        'rounded-xl border-2 px-4 py-2 font-dot text-xs transition',
        checked ? 'border-grass bg-grass/20 text-grass' : 'border-bark/25 bg-white/60 text-bark/60',
      ].join(' ')}
    >
      {label}: {checked ? 'ON' : 'OFF'}
    </button>
  );
}

export function SensorPage() {
  const [latest, setLatest] = useState<SensorReading | null>(null);
  const [history, setHistory] = useState<SensorReading[]>([]);
  const [samples, setSamples] = useState<WaterRawSample[]>([]);
  const [events, setEvents] = useState<DeviceEvent[]>([]);
  const [settings, setSettings] = useState<RuntimeSettings | null>(null);
  const [inside, setInside] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const load = async () => {
    setLoading(true);
    setError('');
    try {
      const [l, h, raw, ev] = await Promise.all([
        getLatestSensor(),
        getSensorHistory(20),
        getWaterRawSamples(12),
        listEvents({ event_type: 'proactive_greeting', limit: 5 }),
      ]);
      setLatest(l.latest_merged);
      setSettings(l.runtime_settings ?? null);
      setInside(Boolean(l.distance_inside_threshold));
      setHistory(h.realtime_history ?? []);
      setSamples(raw.samples ?? []);
      setEvents(ev.events ?? []);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'load failed');
    } finally {
      setLoading(false);
    }
  };

  const patchSettings = async (patch: Partial<RuntimeSettings>) => {
    setError('');
    try {
      const result = await updateRuntimeSettings(patch);
      setSettings(result.settings);
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'settings update failed');
    }
  };

  const testDistanceGreeting = async () => {
    setError('');
    try {
      await ingestRealtimeSensor({ light: Number(latest?.light ?? 700), distance: 49 });
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'distance test failed');
    }
  };

  useEffect(() => {
    void load();
    const t = setInterval(() => void load(), 5000);
    return () => clearInterval(t);
  }, []);

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="font-pixel text-xl text-grass">Sensor</h1>
          <p className="font-dot text-xs text-bark/60">DB에 저장된 센서값과 거리 인사 모드를 확인합니다.</p>
        </div>
        <button
          onClick={() => void load()}
          className="rounded-lg border-2 border-grass bg-grass/10 px-3 py-1 font-dot text-xs text-grass hover:bg-grass/20"
        >
          {loading ? 'loading...' : 'refresh'}
        </button>
      </div>

      {error && (
        <div className="rounded-lg border-2 border-heart-red bg-heart-red/10 p-3 font-dot text-sm text-heart-red">
          {error}
        </div>
      )}

      <div className="pixel-card space-y-3">
        <div className="flex flex-wrap items-center gap-2">
          <Toggle
            label="거리 감지"
            checked={Boolean(settings?.distance_detection_enabled)}
            onChange={(next) => void patchSettings({ distance_detection_enabled: next })}
          />
          <Toggle
            label="호출 모드"
            checked={Boolean(settings?.wake_enabled)}
            onChange={(next) => void patchSettings({ wake_enabled: next })}
          />
          <Toggle
            label="웹 음성모드"
            checked={Boolean(settings?.web_voice_enabled)}
            onChange={(next) => void patchSettings({ web_voice_enabled: next })}
          />
          <button
            type="button"
            onClick={() => void testDistanceGreeting()}
            className="rounded-xl border-2 border-sky bg-sky/15 px-4 py-2 font-dot text-xs text-sky hover:bg-sky/25"
          >
            49cm 테스트
          </button>
        </div>
        <div className="font-dot text-xs text-bark/60">
          threshold {settings?.distance_threshold_cm ?? 50}cm · 현재 {inside ? '50cm 안쪽' : '50cm 바깥'}
        </div>
      </div>

      <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
        <Metric label="Temperature" value={latest?.temperature} suffix="C" />
        <Metric label="Humidity" value={latest?.humidity} suffix="%" />
        <Metric label="Light" value={latest?.light} suffix="lux" />
        <Metric label="Water" value={latest?.water_level} suffix="%" />
        <Metric label="Water Raw" value={latest?.water_raw} />
        <Metric label="Distance" value={latest?.distance} suffix="cm" />
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <div className="pixel-card">
          <h2 className="font-pixel text-sm text-bark">Realtime History</h2>
          <table className="mt-3 w-full font-dot text-xs">
            <thead>
              <tr className="border-b-2 border-bark/30 text-left text-bark/70">
                <th className="py-1 pr-3">Time</th>
                <th className="py-1 pr-3">Light</th>
                <th className="py-1">Distance</th>
              </tr>
            </thead>
            <tbody>
              {history.map((row, i) => (
                <tr key={`${row.reading_id ?? i}`} className="border-b border-bark/10">
                  <td className="py-1 pr-3 text-bark/60">{row.created_at ? new Date(row.created_at).toLocaleTimeString('ko-KR') : '-'}</td>
                  <td className="py-1 pr-3">{row.light ?? '-'}</td>
                  <td className="py-1">{row.distance ?? '-'}cm</td>
                </tr>
              ))}
              {history.length === 0 && <tr><td colSpan={3} className="py-3 text-center text-bark/50">No history.</td></tr>}
            </tbody>
          </table>
        </div>

        <div className="pixel-card">
          <h2 className="font-pixel text-sm text-bark">Water Raw Samples</h2>
          <div className="mt-3 space-y-2">
            {samples.map((sample) => (
              <div key={sample.sample_id} className="flex justify-between rounded-lg border border-bark/15 bg-white/60 p-2 font-dot text-xs">
                <span>{new Date(sample.created_at).toLocaleString('ko-KR')}</span>
                <strong>{sample.raw_value}</strong>
              </div>
            ))}
            {samples.length === 0 && <div className="font-dot text-xs text-bark/50">No raw samples.</div>}
          </div>
        </div>
      </div>

      <div className="pixel-card">
        <h2 className="font-pixel text-sm text-bark">Recent Distance Greetings</h2>
        <div className="mt-3 space-y-2">
          {events.map((event) => (
            <div key={event.event_id} className="rounded-lg border border-bark/15 bg-white/60 p-2 font-dot text-xs">
              <div className="text-bark">{event.generated_text || '-'}</div>
              <div className="mt-1 text-bark/50">
                {new Date(event.created_at).toLocaleString('ko-KR')} · {event.status ?? (event.played ? 'played' : 'pending')} · {event.distance ?? '-'}cm
              </div>
            </div>
          ))}
          {events.length === 0 && <div className="font-dot text-xs text-bark/50">No greeting events.</div>}
        </div>
      </div>
    </div>
  );
}
