import { useState } from 'react';
import { resolveVoiceNamePreference, setStoredVoiceName } from '../api';
import '../styles/settings.css';

type VoiceName = 'F1' | 'F2';

type PersonaItem = {
  id: number;
  text: string;
};

export function SettingsPage() {
  const [notificationEnabled, setNotificationEnabled] = useState(false);
  const [voiceName, setVoiceName] = useState<VoiceName>(() => resolveVoiceNamePreference(['F1', 'F2']) as VoiceName);
  const [isVersionModalOpen, setIsVersionModalOpen] = useState(false);
  const [personaText, setPersonaText] = useState('');
  const [personaItems, setPersonaItems] = useState<PersonaItem[]>([]);
  const [selectedPersonaId, setSelectedPersonaId] = useState<number | null>(null);

  const notificationIcon = notificationEnabled ? '/images/incoming/icon-notification.png' : '/images/incoming/silent2.png';
  const voiceIcon = voiceName === 'F1' ? '/images/incoming/female.png' : '/images/incoming/man.png';
  const versionIcon = '/images/incoming/list.png';

  const selectedPersonaText = personaItems.find((item) => item.id === selectedPersonaId)?.text ?? '선택된 항목 없음';
  const visiblePersonaItems = personaItems.slice(0, 5);

  const handleAddPersona = () => {
    const trimmed = personaText.trim();
    if (!trimmed || personaItems.length >= 5) return;

    const newItem = { id: Date.now(), text: trimmed };
    setPersonaItems((current) => [newItem, ...current]);
    setSelectedPersonaId(newItem.id);
    setPersonaText('');
  };

  const handleRemovePersona = (id: number) => {
    setPersonaItems((current) => current.filter((item) => item.id !== id));
    setSelectedPersonaId((current) => (current === id ? null : current));
  };

  return (
    <div className="settings-page">
      <section className="settings-screen" aria-label="설정 화면">
        <div className="settings-board">
          <div className="settings-board__header">
            <h2 className="settings-board__title">설정</h2>
          </div>

          <div className="settings-grid">
            <button
              type="button"
              className={`settings-button settings-button--notification ${notificationEnabled ? 'is-on' : 'is-off'}`}
              onClick={() => setNotificationEnabled((current) => !current)}
              aria-pressed={notificationEnabled}
            >
              <img className="settings-button__icon" src={notificationIcon} alt="" aria-hidden="true" />
              <span className="settings-button__title">알림</span>
            </button>

            <button
              type="button"
              className={`settings-button settings-button--voice ${voiceName === 'F1' ? 'is-female' : 'is-male'}`}
              onClick={() =>
                setVoiceName((current) => {
                  const next = current === 'F1' ? 'F2' : 'F1';
                  setStoredVoiceName(next);
                  return next;
                })
              }
              aria-pressed={voiceName === 'F1'}
            >
              <img className="settings-button__icon" src={voiceIcon} alt="" aria-hidden="true" />
              <span className="settings-button__title">{voiceName}</span>
            </button>

            <button
              type="button"
              className="settings-button settings-button--version"
              onClick={() => setIsVersionModalOpen(true)}
              aria-pressed={isVersionModalOpen}
            >
              <img className="settings-button__icon" src={versionIcon} alt="" aria-hidden="true" />
              <span className="settings-button__title">버전</span>
            </button>
          </div>
        </div>

        <img
          className="settings-screen__grass"
          src="/images/incoming/grass-pattern3-1.png"
          alt=""
          aria-hidden="true"
        />
        <img
          className="settings-screen__grass settings-screen__grass--right"
          src="/images/incoming/grass-pattern3-1.png"
          alt=""
          aria-hidden="true"
        />
      </section>

      {isVersionModalOpen ? (
        <div className="settings-modal" role="dialog" aria-modal="true" aria-label="버전 선택">
          <button type="button" className="settings-modal__backdrop" onClick={() => setIsVersionModalOpen(false)} aria-label="모달 닫기" />

          <div className="settings-modal__panel">
            <div className="settings-modal__header">
              <h3 className="settings-modal__title">입력한 내용 목록</h3>
              <button type="button" className="settings-modal__close" onClick={() => setIsVersionModalOpen(false)} aria-label="닫기">
                ×
              </button>
            </div>

            <div className="settings-modal__list" aria-label="등록된 내용 목록">
              {visiblePersonaItems.length === 0 ? <div className="settings-modal__empty">아직 등록된 내용이 없어요.</div> : null}
              {visiblePersonaItems.map((item, index) => {
                const selected = selectedPersonaId === item.id;
                return (
                  <div
                    key={item.id}
                    role="button"
                    tabIndex={0}
                    className={`settings-modal__item ${selected ? 'is-selected' : ''}`}
                    onClick={() => setSelectedPersonaId(item.id)}
                    onKeyDown={(event) => {
                      if (event.key === 'Enter' || event.key === ' ') {
                        event.preventDefault();
                        setSelectedPersonaId(item.id);
                      }
                    }}
                  >
                    <span className="settings-modal__item-badge">{index + 1}</span>
                    <span className="settings-modal__item-text">{item.text}</span>
                    <span className="settings-modal__item-select">{selected ? '선택됨' : '선택'}</span>
                    <button
                      type="button"
                      className="settings-modal__item-remove"
                      onClick={(event) => {
                        event.stopPropagation();
                        handleRemovePersona(item.id);
                      }}
                      aria-label="목록 삭제"
                    >
                      ×
                    </button>
                  </div>
                );
              })}
            </div>

            <div className="settings-modal__composer">
              <input
                className="settings-modal__input"
                type="text"
                value={personaText}
                onChange={(event) => setPersonaText(event.target.value)}
                placeholder="내용을 입력해 주세요"
                onKeyDown={(event) => {
                  if (event.key === 'Enter') {
                    event.preventDefault();
                    handleAddPersona();
                  }
                }}
              />

              <button type="button" className="settings-modal__submit" onClick={handleAddPersona}>
                등록
              </button>
            </div>

            <div className="settings-modal__current">현재 선택: {selectedPersonaText}</div>
          </div>
        </div>
      ) : null}
    </div>
  );
}
