import '../styles/settings.css';

type SettingCard = {
  title: string;
  description: string;
  buttonLabel: string;
  tone: 'connected' | 'sensor' | 'voice' | 'ai';
  icon: string;
};

const SETTING_CARDS: SettingCard[] = [
  {
    title: '기기 연결',
    description: '센서 기기와 연결 상태를 확인해요.',
    buttonLabel: '현재 상태: ON',
    tone: 'connected',
    icon: '/images/incoming/button_gr.png',
  },
  {
    title: '센서 설정',
    description: '온도, 습도, 수위, 조도 기준값을 조정해요.',
    buttonLabel: '바로가기',
    tone: 'sensor',
    icon: '/images/incoming/icon_temperature.png',
  },
  {
    title: '보이스 설정',
    description: '마리모의 목소리와 음성 응답을 바꿔요.',
    buttonLabel: '바로가기',
    tone: 'voice',
    icon: '/images/incoming/marimo-shadow-medium.png',
  },
  {
    title: 'AI 설정',
    description: '답변 스타일과 관리 방식을 설정해요.',
    buttonLabel: '바로가기',
    tone: 'ai',
    icon: '/images/incoming/grass-pattern3-1.png',
  },
];

export function SettingsPage() {
  return (
    <div className="settings-page">
      <section className="settings-screen" aria-label="설정 화면">
        <div className="settings-board">
          <div className="settings-board__header">
            <h2 className="settings-board__title">AI 돌봄 설정</h2>
          </div>

          <div className="settings-grid">
            {SETTING_CARDS.map((card) => (
              <article key={card.title} className={`settings-card settings-card--${card.tone}`}>
                <div className="settings-card__icon-wrap" aria-hidden="true">
                  <img className="settings-card__icon" src={card.icon} alt="" />
                </div>

                <h3 className="settings-card__title">{card.title}</h3>
                <div className="settings-card__rule" aria-hidden="true">
                  <span />
                  <img src="/images/incoming/button_be.png" alt="" aria-hidden="true" />
                  <span />
                </div>
                <p className="settings-card__desc">{card.description}</p>

                <button type="button" className={`settings-card__button settings-card__button--${card.tone}`}>
                  {card.buttonLabel}
                </button>
              </article>
            ))}
          </div>
        </div>
      </section>
    </div>
  );
}
