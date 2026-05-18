import { MarimoSpeech } from '../components/MarimoSpeech';
import { PixelCard } from '../components/PixelCard';

export function ReportPage() {
  return (
    <div className="flex flex-col gap-4">
      <MarimoSpeech text="이번 주 리포트야!" />
      <div className="flex gap-2 justify-center">
        <button className="nav-tab active">Weekly</button>
        <button className="nav-tab inactive">Monthly</button>
      </div>
      <PixelCard title="📈 센서 추이">
        <div className="h-32 bg-sky/20 border border-bark/20 rounded flex items-end justify-around p-2 gap-1">
          {['월','화','수','목','금','토','일'].map((d, i) => {
            const h = [60, 75, 65, 80, 70, 85, 78][i];
            return <div key={d} className="flex flex-col items-center gap-0.5 flex-1">
              <div className="w-full bg-grass rounded-sm" style={{ height: `${h}%` }} />
              <span className="font-dot text-[0.5rem] text-bark/60">{d}</span>
            </div>;
          })}
        </div>
      </PixelCard>
    </div>
  );
}
