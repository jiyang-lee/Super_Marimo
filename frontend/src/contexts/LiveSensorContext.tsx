import { createContext, useCallback, useContext, useEffect, useRef, useState, type ReactNode } from 'react';
import { getLatestSensor, type SensorLatest } from '../api';

type LiveSensorStatus = 'loading' | 'ready' | 'error';

interface LiveSensorContextValue {
  sensor: SensorLatest | null;
  status: LiveSensorStatus;
  error: string | null;
  syncedAt: string | null;
  refresh: () => Promise<SensorLatest | null>;
}

const LiveSensorContext = createContext<LiveSensorContextValue | null>(null);
const POLL_INTERVAL_MS = 1000;
const STALE_AFTER_MS = 15000;

function getReadingAgeMs(sensor: SensorLatest): number | null {
  const createdAt = sensor.latest_realtime?.created_at;
  if (!createdAt) return null;

  const timestamp = new Date(createdAt).getTime();
  if (!Number.isFinite(timestamp)) return null;
  return Date.now() - timestamp;
}

function formatAge(ageMs: number): string {
  const seconds = Math.max(0, Math.round(ageMs / 1000));
  if (seconds < 60) return `${seconds}초 전`;
  const minutes = Math.round(seconds / 60);
  return `${minutes}분 전`;
}

export function LiveSensorProvider({ children }: { children: ReactNode }) {
  const [sensor, setSensor] = useState<SensorLatest | null>(null);
  const [status, setStatus] = useState<LiveSensorStatus>('loading');
  const [error, setError] = useState<string | null>(null);
  const [syncedAt, setSyncedAt] = useState<string | null>(null);
  const inFlightRef = useRef(false);
  const mountedRef = useRef(true);
  const sensorRef = useRef<SensorLatest | null>(null);

  const refresh = useCallback(async () => {
    if (inFlightRef.current) {
      return sensorRef.current;
    }

    inFlightRef.current = true;
    try {
      const next = await getLatestSensor();
      if (!mountedRef.current) {
        return next;
      }

      const ageMs = getReadingAgeMs(next);
      if (ageMs === null || ageMs > STALE_AFTER_MS) {
        setSensor(null);
        sensorRef.current = null;
        setStatus('error');
        setError(ageMs === null ? '실시간 센서 수신 시간이 없습니다.' : `실시간 센서 수신이 멈췄습니다. 마지막 수신: ${formatAge(ageMs)}`);
        setSyncedAt(null);
        return null;
      }

      setSensor(next);
      sensorRef.current = next;
      setStatus('ready');
      setError(null);
      setSyncedAt(new Date().toLocaleTimeString('ko-KR'));
      return next;
    } catch (err) {
      if (mountedRef.current) {
        setSensor(null);
        sensorRef.current = null;
        setStatus('error');
        setError(err instanceof Error ? err.message : 'sensor unavailable');
        setSyncedAt(null);
      }
      return null;
    } finally {
      inFlightRef.current = false;
    }
  }, []);

  useEffect(() => {
    mountedRef.current = true;

    const tick = () => {
      void refresh();
    };

    tick();
    const timer = setInterval(tick, POLL_INTERVAL_MS);
    return () => {
      mountedRef.current = false;
      clearInterval(timer);
    };
  }, [refresh]);

  return (
    <LiveSensorContext.Provider value={{ sensor, status, error, syncedAt, refresh }}>
      {children}
    </LiveSensorContext.Provider>
  );
}

export function useLiveSensor() {
  const context = useContext(LiveSensorContext);
  if (!context) {
    throw new Error('useLiveSensor must be used within LiveSensorProvider');
  }
  return context;
}
