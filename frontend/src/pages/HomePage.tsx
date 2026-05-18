import { MarimoSpeech } from '../components/MarimoSpeech';
import { PixelCard } from '../components/PixelCard';
import { PixelButton } from '../components/PixelButton';

export function HomePage() {
  return (
    <div className="flex flex-col gap-4">
      <MarimoSpeech text="오늘도 잘 부탁해!" />
      <PixelCard title="📢 공지사항">
        <ul className="font-dot text-sm text-bark/80 space-y-1">
          <li>• 마리모 케어 가이드가 업데이트되었어요</li>
          <li>• 센서 알림 기능이 추가되었어요</li>
          <li>• 새로운 퀘스트가 열렸어요!</li>
        </ul>
      </PixelCard>
      <PixelCard title="🏆 오늘의 퀘스트">
        <div className="space-y-1">
          {[
            { icon: '💧', label: '물 주기', done: true },
            { icon: '🫗', label: '물 갈기', done: true },
            { icon: '☀️', label: '햇빛 확인', done: false },
            { icon: '💗', label: '사랑 주기', done: false },
          ].map(q => (
            <div key={q.label} className="quest-item">
              <div className="quest-icon bg-sky/30">{q.icon}</div>
              <span className="font-dot flex-1 text-sm">{q.label}</span>
              <PixelButton size="sm" variant={q.done ? 'green' : 'gold'}>
                {q.done ? '완료' : '실행'}
              </PixelButton>
            </div>
          ))}
        </div>
      </PixelCard>
    </div>
  );
}
