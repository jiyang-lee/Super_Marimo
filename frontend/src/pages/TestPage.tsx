import { useEffect, useMemo, useState } from 'react';
import {
  getLatestSensor,
  getRuntimeSettings,
  listEvents,
  updateRuntimeSettings,
  type DeviceEvent,
  type RuntimeSettings,
  type SensorLatest,
} from '../api';

function formatValue(value: unknown, suffix = '') {
  if (value === null || value === undefined || value === '') return '-';
  return `${value}${suffix}`;
}

function timeLabel(value?: string | null) {
  if (!value) return '-';
  return new Date(value).toLocaleTimeString('ko-KR', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
}

function isWebMode(settings: RuntimeSettings | null) {
  return settings?.web_voice_enabled !== false;
}

export function TestPage() {
  const [settings, setSettings] = useState<RuntimeSettings | null>(null);
  const [sensor, setSensor] = useState<SensorLatest | null>(null);
  const [events, setEvents] = useState<DeviceEvent[]>([]);
  const [error, setError] = useState('');
  const [syncedAt, setSyncedAt] = useState('');
  const [savingMode, setSavingMode] = useState(false);

  const webMode = isWebMode(settings);
  const mergedSensor = sensor?.latest_merged ?? sensor?.latest_realtime ?? null;

  const distanceAlerts = useMemo(
    () =>
      events.filter(
        (event) =>
          event.event_type === 'proactive_greeting' ||
          event.event_type === 'sensor_warning' ||
          event.generated_text.includes('거리'),
      ),
    [events],
  );

  const sensorCards = useMemo(
    () => [
      { label: '온도', value: formatValue(mergedSensor?.temperature, '°C') },
      { label: '습도', value: formatValue(mergedSensor?.humidity, '%') },
      { label: '조도', value: formatValue(mergedSensor?.light) },
      { label: '수위', value: formatValue(mergedSensor?.water_level) },
      { label: '거리', value: formatValue(mergedSensor?.distance, 'cm') },
    ],
    [mergedSensor],
  );

  const currentCards = useMemo(
    () => [
      {
        label: '거리 감지 상태',
        value: settings?.distance_detection_enabled ? 'ON' : 'OFF',
        tone: settings?.distance_detection_enabled ? 'lab-pill-ok' : 'lab-pill-warn',
      },
      {
        label: '호출어 상태',
        value: settings?.wake_enabled ? 'ON' : 'OFF',
        tone: settings?.wake_enabled ? 'lab-pill-ok' : 'lab-pill-warn',
      },
      {
        label: '임계치 내부',
        value: settings?.distance_inside_threshold ? 'IN' : 'OUT',
        tone: settings?.distance_inside_threshold ? 'lab-pill-ok' : 'lab-pill-warn',
      },
    ],
    [settings?.distance_detection_enabled, settings?.wake_enabled, settings?.distance_inside_threshold],
  );

  const refreshBoard = async () => {
    setError('');
    try {
      const [nextSettings, nextSensor, nextEvents] = await Promise.all([
        getRuntimeSettings(),
        getLatestSensor(),
        listEvents({ limit: 20 }),
      ]);

      setSettings(nextSettings.settings);
      setSensor(nextSensor);
      setEvents(nextEvents.events ?? []);
      setSyncedAt(new Date().toLocaleTimeString('ko-KR'));
    } catch (err) {
      setError(err instanceof Error ? err.message : 'load failed');
    }
  };

  useEffect(() => {
    void refreshBoard();
  }, []);

  const handleModeChange = async (nextWebVoiceEnabled: boolean) => {
    if (savingMode || webMode === nextWebVoiceEnabled) return;

    setSavingMode(true);
    setError('');
    try {
      const next = await updateRuntimeSettings({ web_voice_enabled: nextWebVoiceEnabled });
      setSettings(next.settings);
      await refreshBoard();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'mode update failed');
    } finally {
      setSavingMode(false);
    }
  };

  return (
    <div className="lab-stack">
      <div className="lab-flex-between">
        <div>
          <span className="lab-pill">테스트 페이지</span>
          <div style={{ marginTop: 8, fontSize: 18, fontWeight: 900, color: '#355338' }}>
            웹 대화 모드 / 환경 대화 모드 분리
          </div>
          <div style={{ marginTop: 4, fontSize: 12, color: '#667085' }}>
            {webMode ? '웹 대화 모드' : '환경 대화 모드'} · {webMode ? '거리 감지 OFF · 호출어 OFF' : '거리 감지 ON · 호출어 ON'}
          </div>
        </div>
        <div className="lab-flex-wrap">
          <span style={{ fontSize: 12, color: '#667085', fontFamily: '"Cascadia Mono", "SFMono-Regular", Consolas, monospace' }}>
            sync {syncedAt || '...'}
          </span>
          <button className="lab-btn lab-btn-secondary" onClick={() => void refreshBoard()}>
            새로고침
          </button>
        </div>
      </div>

      {error && <div className="lab-log-item bad">{error}</div>}

      <div className="lab-sub-panel">
        <div className="lab-sub-panel-head">
          <div>
            <h2>동작 모드</h2>
            <p>웹 대화 모드와 환경 대화 모드를 전환합니다.</p>
          </div>
          <div className="lab-mode-switch">
            <button
              type="button"
              className={['lab-mode-button', webMode ? 'is-active' : ''].join(' ')}
              disabled={savingMode}
              onClick={() => void handleModeChange(true)}
            >
              웹 대화 모드
            </button>
            <button
              type="button"
              className={['lab-mode-button', !webMode ? 'is-active' : ''].join(' ')}
              disabled={savingMode}
              onClick={() => void handleModeChange(false)}
            >
              환경 대화 모드
            </button>
          </div>
        </div>
        <div className="lab-sub-panel-body">
          <div className="lab-notice">
            {webMode
              ? '웹 대화 모드에서는 브라우저가 중심이며, 센서 기반 자동 TTS는 비활성화됩니다.'
              : '환경 대화 모드에서는 거리 진입 TTS와 호출어 기반 대화를 사용합니다.'}
          </div>
        </div>
      </div>

      {webMode ? (
        <div className="lab-sub-panel">
          <div className="lab-sub-panel-head">
            <div>
              <h2>센서 값</h2>
              <p>실시간으로 읽히는 현재 센서 값입니다.</p>
            </div>
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
      ) : (
        <div className="lab-stack">
          <div className="lab-env-top">
            <div className="lab-sub-panel lab-env-panel">
              <div className="lab-sub-panel-head">
                <div>
                  <h2>센서 값</h2>
                  <p>환경 대화 모드에서 실제로 반응하는 센서 값입니다.</p>
                </div>
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

            <div className="lab-sub-panel lab-env-panel">
              <div className="lab-sub-panel-head">
                <div>
                  <h2>현재 설정</h2>
                  <p>환경 대화 모드에서는 이 설정이 실제 동작을 결정합니다.</p>
                </div>
              </div>
              <div className="lab-sub-panel-body lab-settings-body">
                <div className="lab-grid-2 lab-settings-grid">
                  {currentCards.map((card) => (
                    <div key={card.label} className="lab-card lab-card-column">
                      <div className="lab-card-label">{card.label}</div>
                      <div className={`lab-pill ${card.tone}`}>{card.value}</div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>

          <div className="lab-sub-panel">
            <div className="lab-sub-panel-head">
              <div>
                <h2>거리 감지 알림</h2>
                <p>환경 대화 모드에서 생성된 거리 진입 이벤트입니다.</p>
              </div>
            </div>
            <div className="lab-sub-panel-body">
              {distanceAlerts.length === 0 ? (
                <div className="lab-notice">최근 거리 감지 알림이 없습니다.</div>
              ) : (
                <div className="lab-log-list">
                  {distanceAlerts.slice(0, 5).map((event) => (
                    <div key={event.event_id} className="lab-log-item alert">
                      <div className="lab-flex-between" style={{ width: '100%' }}>
                        <span className="lab-log-time">{event.event_type}</span>
                        <span className="lab-pill lab-pill-warn">{event.trigger_source || 'sensor'}</span>
                      </div>
                      <div style={{ marginTop: 6, color: '#1f2937' }}>{event.generated_text || '-'}</div>
                      <div style={{ marginTop: 4, fontSize: 12, color: '#667085' }}>
                        거리 {event.distance ?? '-'}cm · {timeLabel(event.created_at)}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
