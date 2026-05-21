import { useEffect, useState, type ReactNode } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { LiveSensorProvider } from '../contexts/LiveSensorContext';

const NAV_ITEMS = [
  { path: '/home', label: 'HOME' },
  { path: '/sensor', label: 'SENSOR' },
  { path: '/chat', label: 'CHAT' },
  { path: '/settings', label: 'SETTINGS' },
  { path: '/lab', label: 'LAB' },
];

function makeClock() {
  return new Intl.DateTimeFormat('ko-KR', {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: false,
  }).format(new Date());
}

export function Layout({ children }: { children: ReactNode }) {
  const location = useLocation();
  const [clockText, setClockText] = useState(makeClock());

  useEffect(() => {
    const clockTimer = setInterval(() => setClockText(makeClock()), 1000);
    return () => {
      clearInterval(clockTimer);
    };
  }, []);

  useEffect(() => {
    const prevBodyOverflow = document.body.style.overflow;
    const prevHtmlOverflow = document.documentElement.style.overflow;
    if (location.pathname === '/chat') {
      document.body.style.overflow = 'hidden';
      document.documentElement.style.overflow = 'hidden';
    } else {
      document.body.style.overflow = prevBodyOverflow;
      document.documentElement.style.overflow = prevHtmlOverflow;
    }

    return () => {
      document.body.style.overflow = prevBodyOverflow;
      document.documentElement.style.overflow = prevHtmlOverflow;
    };
  }, [location.pathname]);

  return (
    <LiveSensorProvider>
      <div className="app-shell">
        <header className="app-header">
          <div className="header-inner">
            <div className="brand-block">
              <img className="brand-logo" src="/images/incoming/transparent_rogo_3.png" alt="MARIMO QUEST" />
            </div>

            <nav className="top-nav" aria-label="주요 페이지 이동">
              {NAV_ITEMS.map((item) => {
                const active = location.pathname === item.path;
                return (
                  <Link key={item.path} to={item.path} className={`nav-button ${active ? 'is-active' : ''}`}>
                    {item.label}
                  </Link>
                );
              })}
            </nav>

            <div className="status-clock">{clockText}</div>

            {/* 하트 영역은 잠시 비활성화
            <div className="status-hearts" aria-hidden="true">
              {[0, 1, 2].map((index) => (
                <img
                  key={index}
                  className={index < 3 ? 'heart on' : 'heart'}
                  src="/images/incoming/heart_object.png"
                  alt=""
                />
              ))}
            </div>
            */}
          </div>
        </header>

        <main className={`app-main ${location.pathname === '/chat' ? 'is-chat' : ''}`}>{children}</main>
      </div>
    </LiveSensorProvider>
  );
}
