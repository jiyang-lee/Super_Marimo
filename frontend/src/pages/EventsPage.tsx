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
    <div className="lab-stack">
      <div className="lab-flex-between">
        <span className="lab-pill">Device Events</span>
        <span style={{ fontSize: 12, color: '#667085' }}>
          {events.length} records
        </span>
      </div>

      <div className="lab-mode-switch">
        {EVENT_TYPES.map((t) => (
          <button
            key={t.key}
            type="button"
            onClick={() => setFilter(t.key)}
            className={['lab-mode-button', filter === t.key ? 'is-active' : ''].join(' ')}
          >
            {t.label}
          </button>
        ))}
      </div>

      {error && (
        <div className="lab-log-item bad">
          {error}
        </div>
      )}

      <div className="lab-table-wrap">
        <table>
          <thead>
            <tr>
              <th>Type</th>
              <th>Device</th>
              <th>Text</th>
              <th>Played</th>
              <th>Time</th>
            </tr>
          </thead>
          <tbody>
            {loading && (
              <tr>
                <td colSpan={5} style={{ textAlign: 'center', color: '#667085', padding: 24 }}>
                  loading...
                </td>
              </tr>
            )}
            {!loading && events.length === 0 && (
              <tr>
                <td colSpan={5} style={{ textAlign: 'center', color: '#667085', padding: 24 }}>
                  No events.
                </td>
              </tr>
            )}
            {events.map((ev) => (
              <tr key={ev.event_id}>
                <td>
                  <span className="lab-pill">{ev.event_type}</span>
                </td>
                <td style={{ color: '#667085' }}>{ev.device_id || '-'}</td>
                <td style={{ maxWidth: 280, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                  {ev.generated_text || '-'}
                </td>
                <td>
                  <span className={`lab-pill ${ev.played ? 'lab-pill-ok' : 'lab-pill-warn'}`}>
                    {ev.played ? 'yes' : 'no'}
                  </span>
                </td>
                <td style={{ color: '#667085', fontFamily: '"Cascadia Mono", "SFMono-Regular", Consolas, monospace', fontSize: 12 }}>
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
