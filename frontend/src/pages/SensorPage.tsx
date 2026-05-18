import { useEffect, useState } from 'react';
import { getLatestSensor, getSensorHistory, type SensorReading } from '../api';

function Metric({ label, value, suffix }: { label: string; value: string | number | null | undefined; suffix?: string }) {
  const text = value === null || value === undefined || value === '' ? '-' : `${value}${suffix ?? ''}`;
  return (
    <div className="sensor-card">
      <span className="font-dot text-[10px] uppercase tracking-wider text-bark/60">{label}</span>
      <span className="font-pixel text-lg text-bark">{text}</span>
    </div>
  );
}

export function SensorPage() {
  const [latest, setLatest] = useState<SensorReading | null>(null);
  const [history, setHistory] = useState<SensorReading[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const load = async () => {
    setLoading(true);
    setError('');
    try {
      const l = await getLatestSensor();
      const h = await getSensorHistory(10);
      setLatest(l.latest_merged);
      setHistory(h.realtime_history ?? []);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'load failed');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void load();
    const t = setInterval(() => void load(), 10000);
    return () => clearInterval(t);
  }, []);

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center justify-between">
        <h1 className="font-pixel text-xl text-grass">Sensor</h1>
        <button
          onClick={() => void load()}
          className="rounded-lg border-2 border-grass bg-grass/10 px-3 py-1 font-dot text-xs text-grass hover:bg-grass/20"
        >
          refresh
        </button>
      </div>

      {error && (
        <div className="rounded-lg border-2 border-heart-red bg-heart-red/10 p-3 font-dot text-sm text-heart-red">
          {error}
        </div>
      )}

      <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
        <Metric label="Temperature" value={latest?.temperature} suffix="°C" />
        <Metric label="Humidity" value={latest?.humidity} suffix="%" />
        <Metric label="Light" value={latest?.light} />
        <Metric label="Water" value={latest?.water_level} suffix="%" />
        <Metric label="Distance" value={latest?.distance} suffix="cm" />
        <Metric label="Level" value={latest?.state_level} />
      </div>

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
            {history.length === 0 && (
              <tr>
                <td colSpan={3} className="py-3 text-center text-bark/50">
                  {loading ? 'loading...' : 'No history.'}
                </td>
              </tr>
            )}
            {history.map((row, i) => (
              <tr key={i} className="border-b border-bark/10">
                <td className="py-1 pr-3 text-bark/60">
                  {row.created_at ? new Date(row.created_at).toLocaleTimeString('ko-KR') : '-'}
                </td>
                <td className="py-1 pr-3">{row.light ?? '-'}</td>
                <td className="py-1">{row.distance ?? '-'}cm</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
