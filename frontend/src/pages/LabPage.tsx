import '../styles/lab.css';
import { useState } from 'react';
import { DashboardPage } from './DashboardPage';
import { EventsPage } from './EventsPage';
import { TestPage } from './TestPage';

const TABS = [
  { id: 'dashboard', label: 'Dashboard' },
  { id: 'test', label: 'Test' },
  { id: 'events', label: 'Events' },
] as const;

type LabTab = (typeof TABS)[number]['id'];

export function LabPage() {
  const [activeTab, setActiveTab] = useState<LabTab>('dashboard');

  return (
    <div className="lab-page space-y-4">
      <div className="panel-surface p-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <div className="font-dot text-xs uppercase text-cyan-100/70">Operator Lab</div>
            <h1 className="mt-1 text-2xl font-black text-white">운영 콘솔</h1>
          </div>
          <div className="flex rounded-lg border border-white/10 bg-black/20 p-1">
            {TABS.map((tab) => (
              <button
                key={tab.id}
                type="button"
                onClick={() => setActiveTab(tab.id)}
                className={[
                  'rounded-md px-3 py-2 font-dot text-xs transition',
                  activeTab === tab.id ? 'bg-cyan-200 text-slate-950' : 'text-slate-200 hover:bg-white/10',
                ].join(' ')}
              >
                {tab.label}
              </button>
            ))}
          </div>
        </div>
      </div>

      {activeTab === 'dashboard' ? <DashboardPage /> : null}
      {activeTab === 'test' ? <TestPage /> : null}
      {activeTab === 'events' ? <EventsPage /> : null}
    </div>
  );
}
