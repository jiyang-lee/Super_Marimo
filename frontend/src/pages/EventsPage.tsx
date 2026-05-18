import { useEffect, useState } from 'react';
import { listEvents, type DeviceEvent } from '../api';

const EVENT_TYPES = [
  { key: '', label: 'All' },
  { key: 'wakeword', label: 'Wakeword' },
  { key: 'proactive_greeting', label: 'Proactive Greeting' },
  { key: 'sensor_warning', label: 'Sensor Warning' },
  { key: 'manual_test', label: 'Manual Test' },
];

export function EventsPage() {
  const [events, setEvents] = useState<DeviceEvent[]>([]);
  const [filter, setFilter] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const load = async () => {
    setLoading(true);
    setError('');
    try {
      const result = await listEvents({ event_type: filter || undefined, limit: 50 });
      setEvents(result.events ?? []);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'load failed');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void load();
  }, [filter]);

  return (
    <div className="flex flex-col gap-4">
      <h1 className="font-pixel text-xl text-grass">Device Events</h1>

      <div className="flex flex-wrap gap-2">
        {EVENT_TYPES.map((t) => (
          <button
            key={t.key}
            onClick={() => setFilter(t.key)}
            className={[
              'rounded-lg border-2 px-3 py-1 font-dot text-xs transition',
              filter === t.key
                ? 'border-grass bg-grass/15 text-grass'
                : 'border-bark/30 bg-white/50 text-bark hover:border-grass/40',
            ].join(' ')}
          >
            {t.label}
          </button>
        ))}
      </div>

      {error && (
        <div className="rounded-lg border-2 border-heart-red bg-heart-red/10 p-3 font-dot text-sm text-heart-red">
          {error}
        </div>
      )}

      <div className="pixel-card overflow-auto">
        <table className="w-full font-dot text-xs">
          <thead>
            <tr className="border-b-2 border-bark/30 text-left text-bark/70">
              <th className="py-2 pr-4">Type</th>
              <th className="py-2 pr-4">Device</th>
              <th className="py-2 pr-4">Text</th>
              <th className="py-2 pr-4">Played</th>
              <th className="py-2">Time</th>
            </tr>
          </thead>
          <tbody>
            {loading && (
              <tr>
                <td colSpan={5} className="py-4 text-center text-bark/50">
                  loading...
                </td>
              </tr>
            )}
            {!loading && events.length === 0 && (
              <tr>
                <td colSpan={5} className="py-4 text-center text-bark/50">
                  No events.
                </td>
              </tr>
            )}
            {events.map((ev) => (
              <tr key={ev.event_id} className="border-b border-bark/10">
                <td className="py-2 pr-4">
                  <span className="rounded bg-bark/10 px-1.5 py-0.5 text-[10px]">{ev.event_type}</span>
                </td>
                <td className="py-2 pr-4 text-bark/70">{ev.device_id || '-'}</td>
                <td className="max-w-[200px] truncate py-2 pr-4">{ev.generated_text || '-'}</td>
                <td className="py-2 pr-4">
                  <span className={ev.played ? 'text-grass' : 'text-gold'}>
                    {ev.played ? 'yes' : 'no'}
                  </span>
                </td>
                <td className="py-2 text-bark/60">
                  {ev.created_at ? new Date(ev.created_at).toLocaleTimeString('ko-KR') : '-'}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
