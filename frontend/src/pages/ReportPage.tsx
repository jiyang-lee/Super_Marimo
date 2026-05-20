import '../styles/report.css';
const weeklyRows = [
  ['06:00', '23°C', '49%', '82%', '280 lux'],
  ['09:00', '24°C', '47%', '81%', '410 lux'],
  ['12:00', '25°C', '45%', '80%', '620 lux'],
  ['15:00', '24°C', '48%', '79%', '540 lux'],
  ['18:00', '23°C', '52%', '80%', '360 lux'],
  ['21:00', '22°C', '55%', '81%', '240 lux'],
];

export function ReportPage() {
  return (
    <section className="report-page sensor-stack report-screen">
      <article className="sensor-switch-panel">
        <div className="panel-head">
          <h1 className="panel-title">주간 리포트</h1>
          <div className="mode-switch">
            <button type="button" className="mode-button is-active">Weekly</button>
            <button type="button" className="mode-button">Monthly</button>
          </div>
        </div>
        <div className="panel-body">
          <div className="weekly-list">
            {weeklyRows.map(([time, temp, humidity, water, light]) => (
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
