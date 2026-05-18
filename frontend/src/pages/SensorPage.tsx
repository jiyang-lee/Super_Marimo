import { MarimoSpeech } from '../components/MarimoSpeech';
import { PixelCard } from '../components/PixelCard';

export function SensorPage() {
  return (
    <div className="flex flex-col gap-4">
      <MarimoSpeech text="센서 상태를 확인해줘!" />
      <div className="grid grid-cols-2 gap-3">
        {[
          { icon: '🌡️', label: '온도', value: '24℃', color: 'text-heart-red' },
          { icon: '💧', label: '습도', value: '45%', color: 'text-water-blue' },
          { icon: '🚰', label: '수위', value: '80%', color: 'text-water-blue' },
          { icon: '☀️', label: '조도', value: '500lux', color: 'text-sun-orange' },
        ].map(s => (
          <div key={s.label} className="sensor-card">
            <span className="text-2xl">{s.icon}</span>
            <span className={`sensor-value ${s.color}`}>{s.value}</span>
            <span className="font-dot text-xs text-bark/60">{s.label}</span>
          </div>
        ))}
      </div>
      <PixelCard title="📊 센서 이력">
        <table className="w-full font-dot text-xs text-bark/80">
          <thead><tr className="border-b border-bark/30">
            <th className="py-1 text-left">시간</th><th className="py-1">온도</th><th className="py-1">습도</th><th className="py-1">수위</th><th className="py-1">조도</th>
          </tr></thead>
          <tbody>
            {[['12:00','24℃','45%','80%','500lux'],['11:00','23℃','47%','78%','480lux'],['10:00','22℃','50%','76%','450lux']].map(r =>
              <tr key={r[0]} className="border-b border-bark/15"><td className="py-1">{r[0]}</td><td className="text-center">{r[1]}</td><td className="text-center">{r[2]}</td><td className="text-center">{r[3]}</td><td className="text-center">{r[4]}</td></tr>
            )}
          </tbody>
        </table>
      </PixelCard>
    </div>
  );
}
