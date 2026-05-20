import { useEffect, useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { getRuntimeSettings, updateRuntimeSettings, type RuntimeSettings } from '../api';

const NAV_ITEMS = [
  { path: '/', label: 'HOME' },
  { path: '/sensor', label: 'SENSOR' },
  { path: '/settings', label: 'SETTINGS' },
];

function makeClock() {
  return new Intl.DateTimeFormat('ko-KR', {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: false,
  }).format(new Date());
}

export function Layout({ children }: { children: React.ReactNode }) {
  const location = useLocation();
  const [settings, setSettings] = useState<RuntimeSettings | null>(null);
  const [loading, setLoading] = useState(false);
  const [clockText, setClockText] = useState(makeClock());

  const fetchSettings = async () => {
    try {
      const res = await getRuntimeSettings();
      setSettings(res.settings);
    } catch {
      // The visual shell should still render while backend services start.
    }
  };

  useEffect(() => {
    void fetchSettings();
    const settingsTimer = setInterval(() => void fetchSettings(), 3000);
    const clockTimer = setInterval(() => setClockText(makeClock()), 1000);
    return () => {
      clearInterval(settingsTimer);
      clearInterval(clockTimer);
    };
  }, []);

  const toggleMode = async () => {
    if (loading || !settings) return;
    setLoading(true);
    try {
      const res = await updateRuntimeSettings({ web_voice_enabled: !settings.web_voice_enabled });
      setSettings(res.settings);
    } catch (e) {
      alert(e instanceof Error ? e.message : '운영 모드 전환에 실패했습니다.');
    } finally {
      setLoading(false);
    }
  };

  const activeHearts = settings?.web_voice_enabled === false ? 2 : 3;

  return (
    <div className="app-shell">
      <header className="app-header">
        <div className="header-inner">
          <div className="brand-block">
            <img className="brand-logo" src="/images/incoming/transparent_rogo_3.png" alt="MARIMO QUEST" />
          </div>

          <nav className="top-nav" aria-label="주요 화면 이동">
            {NAV_ITEMS.map((item) => {
              const active = location.pathname === item.path;
              return (
                <Link key={item.path} to={item.path} className={`nav-button ${active ? 'is-active' : ''}`}>
                  {item.label}
                </Link>
              );
            })}
          </nav>

          <div className="header-status">
            <button
              type="button"
              className="mode-button header-mode-button"
              disabled={loading || !settings}
              onClick={() => void toggleMode()}
            >
              {settings?.web_voice_enabled === false ? 'DEVICE' : 'WEB'}
            </button>
            <div className="status-hearts" aria-hidden="true">
              {[0, 1, 2].map((index) => (
                <img
                  key={index}
                  className={index < activeHearts ? 'heart on' : 'heart'}
                  src="/images/incoming/heart_object.png"
                  alt=""
                />
              ))}
            </div>
            <div className="status-clock">{clockText}</div>
          </div>
        </div>
      </header>

      <main className="app-main">{children}</main>
    </div>
  );
}
