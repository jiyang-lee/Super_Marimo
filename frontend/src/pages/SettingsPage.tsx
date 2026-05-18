import { MarimoSpeech } from '../components/MarimoSpeech';
import { PixelCard } from '../components/PixelCard';

export function SettingsPage() {
  return (
    <div className="flex flex-col gap-4">
      <MarimoSpeech text="설정 메뉴야!" />
      {[
        { icon: '🔔', label: '알림', desc: '센서 알림 받기' },
        { icon: '💧', label: '센서 설정', desc: '센서 범위 조절' },
        { icon: '📖', label: '가이드', desc: '키우기 4가지 규칙' },
      ].map(item => (
        <PixelCard key={item.label} className="flex items-center gap-3 cursor-pointer hover:bg-parchment-dark/30">
          <span className="text-2xl">{item.icon}</span>
          <div className="flex-1">
            <div className="font-dot font-bold text-bark text-sm">{item.label}</div>
            <div className="font-dot text-xs text-bark/60">{item.desc}</div>
          </div>
          <span className="text-bark/40">▸</span>
        </PixelCard>
      ))}
    </div>
  );
}
