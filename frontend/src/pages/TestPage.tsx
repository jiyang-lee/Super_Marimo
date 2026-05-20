import { useEffect, useMemo, useState } from 'react';
import {
  askChat,
  getLatestSensor,
  getRuntimeSettings,
  getRuntimeSettingsHistory,
  listEvents,
  synthesizeTts,
  updateRuntimeSettings,
  type AskResult,
  type DeviceEvent,
  type RuntimeSettings,
  type RuntimeSettingsHistory,
  type SensorLatest,
} from '../api';

const QUICK_ACTIONS = [
  '현재 상태를 간단히 요약해줘',
  '센서값을 확인해서 이상 여부를 알려줘',
  '오늘 기준으로 먼저 확인할 내용을 알려줘',
  '지금 상황을 운영자 관점으로 정리해줘',
];

function normalizeAnswer(result: AskResult | null) {
  if (!result) return '';
  return result.answer || result.llm_answer || result.tts_text || '';
}

function normalizeSummary(result: AskResult | null) {
  if (!result) return '';
  return result.action_result?.summary || result.session_summary || normalizeAnswer(result);
}

function formatValue(value: unknown, suffix = '') {
  if (value === null || value === undefined || value === '') return '-';
  return `${value}${suffix}`;
}

function timeLabel(value?: string | null) {
  if (!value) return '-';
  return new Date(value).toLocaleTimeString('ko-KR', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
}

function relativeMode(settings: RuntimeSettings | null) {
  return settings?.web_voice_enabled === false ? 'environment' : 'web';
}

export function TestPage() {
  const [settings, setSettings] = useState<RuntimeSettings | null>(null);
  const [sensor, setSensor] = useState<SensorLatest | null>(null);
  const [history, setHistory] = useState<RuntimeSettingsHistory[]>([]);
  const [events, setEvents] = useState<DeviceEvent[]>([]);
  const [lastResult, setLastResult] = useState<AskResult | null>(null);
  const [input, setInput] = useState('');
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [savingMode, setSavingMode] = useState(false);
  const [error, setError] = useState('');
  const [syncedAt, setSyncedAt] = useState('');
  const [speaking, setSpeaking] = useState(false);

  const isWebMode = relativeMode(settings) === 'web';
  const modeLabel = isWebMode ? '웹 대화 모드' : '환경 대화 모드';
  const modeHint = isWebMode
    ? '거리 감지 OFF · 호출어 OFF'
    : '거리 감지 ON · 호출어 ON';
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
      { label: 'Temperature', value: formatValue(mergedSensor?.temperature, '°C') },
      { label: 'Humidity', value: formatValue(mergedSensor?.humidity, '%') },
      { label: 'Light', value: formatValue(mergedSensor?.light) },
      { label: 'Water', value: formatValue(mergedSensor?.water_level) },
      { label: 'Distance', value: formatValue(mergedSensor?.distance, 'cm') },
      { label: 'Level', value: formatValue(mergedSensor?.state_level) },
    ],
    [mergedSensor],
  );

  const currentCards = useMemo(
    () =>
      isWebMode
        ? []
        : [
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
          ],
    [isWebMode, settings?.distance_detection_enabled, settings?.wake_enabled],
  );

  const refreshBoard = async () => {
    setError('');
    try {
      const [nextSettings, nextSensor, nextHistory, nextEvents] = await Promise.all([
        getRuntimeSettings(),
        getLatestSensor(),
        getRuntimeSettingsHistory(12),
        listEvents({ limit: 20 }),
      ]);

      setSettings(nextSettings.settings);
      setSensor(nextSensor);
      setHistory(nextHistory.history ?? []);
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

  const handleSend = async (text: string) => {
    const message = text.trim();
    if (!message || loading) return;

    setLoading(true);
    setError('');
    try {
      const result = await askChat(message, sessionId ?? undefined, true);
      setLastResult(result);
      setSessionId(result.session_id ?? sessionId);
      setInput('');
      await refreshBoard();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'ask failed');
    } finally {
      setLoading(false);
    }
  };

  const playLast = async () => {
    const text = normalizeAnswer(lastResult);
    if (!text || speaking) return;

    setSpeaking(true);
    setError('');
    try {
      const audio = await synthesizeTts(text);
      const url = URL.createObjectURL(audio);
      const player = new Audio(url);
      player.onended = () => URL.revokeObjectURL(url);
      player.onerror = () => URL.revokeObjectURL(url);
      await player.play();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'tts failed');
    } finally {
      setSpeaking(false);
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
          <div style={{ marginTop: 4, fontSize: 12, color: '#667085' }}>{modeLabel} · {modeHint}</div>
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
            <h2>구동 모드</h2>
            <p>모드에 따라 지원하는 기능과 기본값이 달라집니다.</p>
          </div>
          <div className="lab-mode-switch">
            <button
              type="button"
              className={['lab-mode-button', isWebMode ? 'is-active' : ''].join(' ')}
              disabled={savingMode}
              onClick={() => void handleModeChange(true)}
            >
              웹 대화 모드
            </button>
            <button
              type="button"
              className={['lab-mode-button', !isWebMode ? 'is-active' : ''].join(' ')}
              disabled={savingMode}
              onClick={() => void handleModeChange(false)}
            >
              환경 대화 모드
            </button>
          </div>
        </div>
        <div className="lab-sub-panel-body">
          <div className="lab-notice">
            <strong>{modeLabel}</strong>에서는 {modeHint}로 동작합니다.
            {isWebMode
              ? ' 이 모드에서는 거리 감지와 호출어 상태 카드를 숨기고, 센서값만 중심으로 보여줍니다.'
              : ' 이 모드에서는 거리 감지 알림과 상태 카드, 호출어 상태 카드까지 함께 보여줍니다.'}
          </div>
        </div>
      </div>

      <div className="lab-grid-2">
        <div className="lab-stack">
          <div className="lab-sub-panel">
            <div className="lab-sub-panel-head">
              <div>
                <h2>센서값</h2>
                <p>웹 대화 모드에서는 이 영역이 핵심 정보입니다.</p>
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

          {!isWebMode && (
            <div className="lab-sub-panel">
              <div className="lab-sub-panel-head">
                <div>
                  <h2>거리 감지 알림</h2>
                  <p>환경 대화 모드에서만 거리 관련 알림을 보여줍니다.</p>
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
          )}
        </div>

        <div className="lab-stack">
          {!isWebMode && (
            <div className="lab-sub-panel">
              <div className="lab-sub-panel-head">
                <div>
                  <h2>퀵 액션</h2>
                  <p>환경 대화 모드에서만 빠른 테스트 입력을 제공합니다.</p>
                </div>
              </div>
              <div className="lab-sub-panel-body">
                <div className="lab-grid-2" style={{ gridTemplateColumns: 'repeat(2, minmax(0, 1fr))' }}>
                  {QUICK_ACTIONS.map((action) => (
                    <button key={action} type="button" className="lab-quick-card" disabled={loading} onClick={() => void handleSend(action)}>
                      <div style={{ fontWeight: 800, color: '#355338', lineHeight: 1.5 }}>{action}</div>
                    </button>
                  ))}
                </div>
              </div>
            </div>
          )}

          <div className="lab-sub-panel">
            <div className="lab-sub-panel-head">
              <div>
                <h2>직접 대화</h2>
                <p>테스트 메시지를 직접 보내서 응답 순서와 센서 반영을 확인합니다.</p>
              </div>
            </div>
            <div className="lab-sub-panel-body">
              <div className="lab-stack">
                <textarea
                  className="lab-input"
                  rows={5}
                  value={input}
                  onChange={(event) => setInput(event.target.value)}
                  placeholder="예: 지금 상태를 요약해줘"
                />
                <div className="lab-flex-between">
                  <div style={{ fontSize: 12, color: '#667085' }}>
                    세션 {sessionId ? sessionId.slice(0, 8) : '없음'}
                  </div>
                  <div className="lab-flex-wrap">
                    <button
                      type="button"
                      className="lab-btn lab-btn-secondary"
                      onClick={() => setInput('현재 상태를 간단히 요약해줘')}
                    >
                      기본 문장
                    </button>
                    <button type="button" className="lab-btn lab-btn-primary" disabled={loading} onClick={() => void handleSend(input)}>
                      {loading ? '전송 중' : '전송'}
                    </button>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <div className="lab-sub-panel">
            <div className="lab-sub-panel-head">
              <div>
                <h2>마지막 응답</h2>
                <p>응답 결과와 TTS 텍스트를 함께 확인합니다.</p>
              </div>
              <button
                type="button"
                className="lab-btn lab-btn-secondary"
                disabled={!normalizeAnswer(lastResult) || speaking}
                onClick={() => void playLast()}
              >
                {speaking ? '재생 중' : '음성 듣기'}
              </button>
            </div>
            <div className="lab-sub-panel-body">
              {lastResult ? (
                <div className="lab-stack">
                  <div className="lab-notice">
                    <strong>요약</strong>
                    <div style={{ marginTop: 6 }}>{normalizeSummary(lastResult) || '-'}</div>
                  </div>
                  <div className="lab-grid-2" style={{ gridTemplateColumns: 'repeat(2, minmax(0, 1fr))' }}>
                    <div className="lab-card lab-card-column">
                      <div className="lab-card-label">응답</div>
                      <div className="lab-card-value" style={{ fontSize: 16, lineHeight: 1.5, whiteSpace: 'normal' }}>
                        {normalizeAnswer(lastResult) || '-'}
                      </div>
                    </div>
                    <div className="lab-card lab-card-column">
                      <div className="lab-card-label">세션 요약</div>
                      <div className="lab-card-value" style={{ fontSize: 16, lineHeight: 1.5, whiteSpace: 'normal' }}>
                        {lastResult.session_summary || '-'}
                      </div>
                    </div>
                  </div>
                </div>
              ) : (
                <div className="lab-notice">아직 응답이 없습니다. 메시지를 보내면 여기에 결과가 표시됩니다.</div>
              )}
            </div>
          </div>

          {!isWebMode && (
            <div className="lab-sub-panel">
              <div className="lab-sub-panel-head">
                <div>
                  <h2>지금 설정</h2>
                  <p>현재 구동 중인 설정을 카드로 보여줍니다.</p>
                </div>
              </div>
              <div className="lab-sub-panel-body">
                <div className="lab-grid-2" style={{ gridTemplateColumns: 'repeat(2, minmax(0, 1fr))' }}>
                  {currentCards.map((card) => (
                    <div key={card.label} className="lab-card lab-card-column">
                      <div className="lab-card-label">{card.label}</div>
                      <div className={`lab-pill ${card.tone}`}>{card.value}</div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}

          {!isWebMode && (
            <div className="lab-sub-panel">
              <div className="lab-sub-panel-head">
                <div>
                  <h2>마지막 설정</h2>
                  <p>설정 변경 이력을 최근순으로 확인합니다.</p>
                </div>
              </div>
              <div className="lab-sub-panel-body">
                {history.length === 0 ? (
                  <div className="lab-notice">설정 변경 기록이 없습니다.</div>
                ) : (
                  <div className="lab-log-list">
                    {history.map((item) => (
                      <div key={item.history_id} className="lab-log-item">
                        <div className="lab-flex-between" style={{ width: '100%' }}>
                          <span className="lab-log-time">{item.setting_key}</span>
                          <span style={{ color: '#667085' }}>{timeLabel(item.changed_at)}</span>
                        </div>
                        <div style={{ marginTop: 6, color: '#1f2937' }}>
                          {item.summary || item.action_type || 'setting updated'}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
