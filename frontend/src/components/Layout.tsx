import { Link, useLocation } from 'react-router-dom';

const NAV_ITEMS = [
  { path: '/', label: 'Dashboard' },
  { path: '/events', label: 'Events' },
  { path: '/test', label: 'Test' },
  { path: '/home', label: 'Home' },
  { path: '/sensor', label: 'Sensor' },
  { path: '/report', label: 'Report' },
  { path: '/settings', label: 'Settings' },
];

export function Layout({ children }: { children: React.ReactNode }) {
  const location = useLocation();

  return (
    <div className="min-h-screen bg-parchment text-bark">
      <nav className="sticky top-0 z-50 border-b-2 border-bark bg-parchment/95 backdrop-blur">
        <div className="mx-auto flex max-w-7xl flex-wrap items-center gap-2 px-4 py-3">
          <span className="font-pixel text-lg text-grass">Super Marimo</span>
          <div className="ml-auto flex flex-wrap gap-2">
            {NAV_ITEMS.map((item) => {
              const active = location.pathname === item.path;
              return (
                <Link
                  key={item.path}
                  to={item.path}
                  className={[
                    'rounded-lg border-2 px-3 py-1 font-dot text-xs transition',
                    active
                      ? 'border-grass bg-grass/20 text-grass'
                      : 'border-bark/30 bg-white/50 text-bark hover:border-grass/60',
                  ].join(' ')}
                >
                  {item.label}
                </Link>
              );
            })}
          </div>
        </div>
      </nav>
      <main className="mx-auto max-w-7xl px-4 py-6">{children}</main>
    </div>
  );
}
