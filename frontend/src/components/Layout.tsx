import { useEffect, useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { getRuntimeSettings, updateRuntimeSettings, type RuntimeSettings } from '../api';

const NAV_ITEMS = [
  { path: '/', label: 'Dashboard' },
  { path: '/events', label: 'Events' },
  { path: '/test', label: '놀이방' },
  { path: '/sensor', label: 'Sensor' },
  { path: '/chat', label: 'Chat' },
];

export function Layout({ children }: { children: React.ReactNode }) {
  const location = useLocation();
  const [settings, setSettings] = useState<RuntimeSettings | null>(null);
  const [loading, setLoading] = useState(false);

  const fetchSettings = async () => {
    try {
      const res = await getRuntimeSettings();
      setSettings(res.settings);
    } catch {
      // Ignore background error
    }
  };

  useEffect(() => {
    void fetchSettings();
    // Poll runtime settings occasionally to keep sync
    const timer = setInterval(() => void fetchSettings(), 3000);
    return () => clearInterval(timer);
  }, []);

  const toggleMode = async () => {
    if (loading || !settings) return;
    setLoading(true);
    try {
      const nextWebVoice = !settings.web_voice_enabled;
      const res = await updateRuntimeSettings({ web_voice_enabled: nextWebVoice });
      setSettings(res.settings);
    } catch (e) {
      alert(e instanceof Error ? e.message : '구동 모드 전환에 실패했습니다.');
    } finally {
      setLoading(false);
    }
  };

  const isWebMode = settings?.web_voice_enabled ?? true;

  return (
    <div className="min-h-screen bg-parchment text-bark">
      <nav className="sticky top-0 z-50 border-b-2 border-bark bg-parchment/95 backdrop-blur shadow-sm">
        <div className="mx-auto flex max-w-7xl flex-wrap items-center justify-between gap-3 px-4 py-3">
          <div className="flex items-center gap-3">
            <span className="font-pixel text-lg text-grass">Super Marimo</span>
            
            {/* 글로벌 구동 모드 표시 및 토글 버튼 */}
            {settings && (
              <button
                type="button"
                onClick={() => void toggleMode()}
                disabled={loading}
                className={[
                  'rounded-full border-2 px-3 py-1 font-dot text-[10px] font-bold flex items-center gap-1.5 active:scale-95 transition-all shadow-sm',
                  isWebMode 
                    ? 'border-sky bg-sky/15 text-sky hover:bg-sky/20' 
                    : 'border-emerald-600 bg-emerald-50/15 text-emerald-700 hover:bg-emerald-50/25'
                ].join(' ')}
                title={isWebMode ? '웹 대화 모드 (웹 페이지 버튼 제어 / 호출어 감지 OFF)' : '기기 단독 모드 (기기에서 직접 호출어 "마리모야" 감지 / 버튼 입력 불필요)'}
              >
                <span>{isWebMode ? '🌿 웹 모드 (버튼 제어)' : '🤖 기기 모드 (호출어 감지)'}</span>
                <span className="w-1.5 h-1.5 rounded-full bg-current animate-pulse" />
              </button>
            )}
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <div className="flex flex-wrap gap-1.5">
              {NAV_ITEMS.map((item) => {
                const active = location.pathname === item.path;
                return (
                  <Link
                    key={item.path}
                    to={item.path}
                    className={[
                      'rounded-lg border-2 px-3 py-1 font-dot text-xs font-bold transition-all duration-200',
                      active
                        ? 'border-grass bg-grass/20 text-grass shadow-sm'
                        : 'border-bark/10 bg-white/40 text-bark hover:border-grass/50 hover:bg-white/70',
                    ].join(' ')}
                  >
                    {item.label}
                  </Link>
                );
              })}
            </div>
          </div>
        </div>
      </nav>
      <main className="mx-auto max-w-7xl px-4 py-6">{children}</main>
    </div>
  );
}
