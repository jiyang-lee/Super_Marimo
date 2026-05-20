import '../styles/home.css';
import { MarimoImage } from '../components/MarimoImage';

const homeNotices = [
  '오늘 마리모 상태를 먼저 확인하고 작은 퀘스트를 하나씩 진행해 주세요.',
  '물, 습도, 조도 기록은 Sensor 화면에서 더 자세한 그래프로 볼 수 있어요.',
  '웹 모드에서는 버튼과 채팅으로, 기기 모드에서는 센서 흐름으로 반응합니다.',
];

const questItems = [
  { id: 'water', icon: '/images/incoming/icon-water.png', title: '물 상태 확인', action: '확인' },
  { id: 'light', icon: '/images/incoming/icon-light.png', title: '빛 상태 확인', action: '확인' },
  { id: 'humidity', icon: '/images/incoming/icon-humidity.png', title: '습도 확인', action: '확인' },
  { id: 'heart', icon: '/images/incoming/heart_object.png', title: '오늘의 성장 체크', action: '확인' },
];

export function HomePage() {
  return (
    <section className="home-stage" aria-label="Home stage">
      <div className="home-stage__layout">
        <section className="home-board home-board--notice" aria-labelledby="home-notice-title">
          <h2 className="home-board__title" id="home-notice-title">
            공지사항
          </h2>
          <div className="home-board__surface">
            <div className="home-board__content home-board__content--notice">
              {homeNotices.map((notice) => (
                <p key={notice}>{notice}</p>
              ))}
            </div>
          </div>
        </section>

        <section className="home-hero" aria-label="Marimo stage">
          <img
            className="home-hero__bubble"
            src="/images/incoming/speech-bubble-horizontal.png"
            alt=""
            aria-hidden="true"
          />
          <div className="home-hero__bubble-copy">오늘도 잘 부탁해!</div>
          <MarimoImage size="large" className="home-hero__marimo" />
        </section>

        <section className="home-board home-board--quest" aria-labelledby="home-quest-title">
          <h2 className="home-board__title" id="home-quest-title">
            오늘의 퀘스트
          </h2>
          <div className="home-board__surface">
            <div className="home-board__content home-board__content--quest">
              {questItems.map((quest) => (
                <label key={quest.id} className="home-quest-item">
                  <input type="checkbox" aria-label={`${quest.title} 완료`} />
                  <span className="home-quest-item__icon">
                    <img src={quest.icon} alt="" aria-hidden="true" />
                  </span>
                  <span className="home-quest-item__title">{quest.title}</span>
                  <span className="home-quest-item__action" aria-hidden="true">
                    {quest.action}
                  </span>
                </label>
              ))}
            </div>
          </div>
        </section>
      </div>
    </section>
  );
}
