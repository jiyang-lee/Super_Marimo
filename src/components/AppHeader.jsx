import { MarimoImage } from "./MarimoImage";

export function AppHeader({
  activeScreen,
  onChangeScreen,
  navigationItems,
  clockText,
}) {
  return (
    <header className="app-header">
      <div className="header-inner">
        <div className="brand-block">
          <div className="brand-logo-wrap">
            <img
              className="brand-logo"
              src="/images/logo/app-logo.svg"
              alt="MARIMO QUEST 로고"
            />
          </div>
          <div className="brand-copy">
            <strong>MARIMO QUEST</strong>
            <span>마리모를 돌보는 반응형 웹앱</span>
          </div>
        </div>

        <nav className="desktop-nav" aria-label="주요 화면 이동">
          {navigationItems.map((item) => (
            <button
              key={item.key}
              className={`nav-button ${activeScreen === item.key ? "is-active" : ""}`}
              type="button"
              onClick={() => onChangeScreen(item.key)}
            >
              {item.label}
            </button>
          ))}
        </nav>

        <div className="header-status">
          <div className="status-hearts" aria-hidden="true">
            <span>♥</span>
            <span>♥</span>
            <span>♥</span>
          </div>
          <div className="status-clock">{clockText}</div>
        </div>
      </div>

      <div className="mobile-top-strip">
        <MarimoImage size="small" alt="작은 마리모 아바타" />
        <span>오늘도 잘 부탁해!</span>
      </div>
    </header>
  );
}
