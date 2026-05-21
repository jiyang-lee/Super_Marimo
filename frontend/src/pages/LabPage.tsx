import { useState } from 'react';
import '../styles/lab.css';
import { DashboardPage } from './DashboardPage';
import { EventsPage } from './EventsPage';
import { TestPage } from './TestPage';

const TABS = [
  { id: 'dashboard', label: '운영 콘솔' },
  { id: 'test', label: '테스트' },
  { id: 'events', label: '이벤트' },
] as const;

type LabTab = (typeof TABS)[number]['id'];

export function LabPage() {
  const [activeTab, setActiveTab] = useState<LabTab>('dashboard');

  return (
    <section className="lab-page">
      <article className="lab-panel">
        <div className="lab-panel-head">
          <div>
            <h1 className="lab-panel-title">관리자 / 개발자 콘솔</h1>
            <p className="lab-panel-subtitle">운영 상태와 테스트 모드를 한곳에서 확인합니다.</p>
          </div>
          <div className="lab-mode-switch">
            {TABS.map((tab) => (
              <button
                key={tab.id}
                type="button"
                onClick={() => setActiveTab(tab.id)}
                className={['lab-mode-button', activeTab === tab.id ? 'is-active' : ''].join(' ')}
              >
                {tab.label}
              </button>
            ))}
          </div>
        </div>

        <div className="lab-panel-body">
          {activeTab === 'dashboard' ? <DashboardPage /> : null}
          {activeTab === 'test' ? <TestPage /> : null}
          {activeTab === 'events' ? <EventsPage /> : null}
        </div>
      </article>
    </section>
  );
}
