import { useState } from 'react';
import '../styles/report.css';

const REPORT_MODES = {
  weekly: {
    label: '주간',
    title: '주간 센서 요약',
    rows: [
      ['06:00', '23°C', '49%', '82%', '280 lux'],
      ['09:00', '24°C', '47%', '81%', '410 lux'],
      ['12:00', '25°C', '45%', '80%', '620 lux'],
      ['15:00', '24°C', '48%', '79%', '540 lux'],
      ['18:00', '23°C', '52%', '80%', '360 lux'],
      ['21:00', '22°C', '55%', '81%', '240 lux'],
    ],
  },
  monthly: {
    label: '월간',
    title: '월간 센서 추세',
    rows: [
      ['1주차', '23°C', '50%', '81%', '320 lux'],
      ['2주차', '24°C', '48%', '80%', '460 lux'],
      ['3주차', '25°C', '46%', '79%', '580 lux'],
      ['4주차', '24°C', '49%', '80%', '390 lux'],
    ],
  },
} as const;

type ReportMode = keyof typeof REPORT_MODES;

export function ReportPage() {
  const [mode, setMode] = useState<ReportMode>('weekly');
  const report = REPORT_MODES[mode];

  return (
    <section className="report-page sensor-stack report-screen">
      <article className="sensor-switch-panel">
        <div className="panel-head">
          <div>
            <h1 className="panel-title">운영 리포트</h1>
            <p className="mt-1 font-dot text-[10px] text-[#355338]/70">{report.title}</p>
          </div>
          <div className="mode-switch">
            <button
              type="button"
              className={['mode-button', mode === 'weekly' ? 'is-active' : ''].join(' ')}
              onClick={() => setMode('weekly')}
            >
              {REPORT_MODES.weekly.label}
            </button>
            <button
              type="button"
              className={['mode-button', mode === 'monthly' ? 'is-active' : ''].join(' ')}
              onClick={() => setMode('monthly')}
            >
              {REPORT_MODES.monthly.label}
            </button>
          </div>
        </div>
        <div className="panel-body">
          <div className="weekly-list">
            {report.rows.map(([time, temp, humidity, water, light]) => (
              <article key={time} className="weekly-card">
                <span className="weekly-date">{time}</span>
                <span className="weekly-text">온도 {temp} / 습도 {humidity} / 수위 {water} / 조도 {light}</span>
              </article>
            ))}
          </div>
        </div>
      </article>
    </section>
  );
}
