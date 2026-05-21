import { useEffect, useMemo, useRef, useState } from 'react';
import {
  checkVoiceHealth,
  getStoredPersonaPreset,
  getStoredVoiceName,
  normalizeVoiceNames,
  PERSONA_PRESETS,
  resolvePersonaPreset,
  resolveVoiceNamePreference,
  setStoredPersonaPreset,
  setStoredVoiceName,
  getRuntimeSettings,
  updateRuntimeSettings,
  type PersonaPresetId,
  type RuntimeSettings,
} from '../api';
import { useLiveSensor } from '../contexts/LiveSensorContext';
import '../styles/settings.css';

type VoiceHealthState = {
  names: string[];
  loaded: boolean;
  error: string;
};

type VoiceGroup = 'female' | 'male';

function groupVoiceNames(names: string[]) {
  const female = names.filter((name) => /^F[1-5]$/.test(name));
  const male = names.filter((name) => /^M[1-5]$/.test(name));
  const other = names.filter((name) => !/^F[1-5]$/.test(name) && !/^M[1-5]$/.test(name));
  return { female, male, other };
}

function getVoiceGroup(name: string): VoiceGroup {
  return /^M[1-5]$/.test(name) ? 'male' : 'female';
}

function getVoiceLabel(name: string): string {
  const match = name.match(/^([FM])(\d)$/);
  if (!match) return name;
  const genderLabel = match[1] === 'F' ? '여자' : '남자';
  return `${genderLabel}${match[2]}`;
}

function VoiceChip({
  name,
  active,
  onClick,
}: {
  name: string;
  active: boolean;
  onClick: (name: string) => void;
}) {
  return (
    <button
      type="button"
      className={`settings-voice-chip ${active ? 'is-active' : ''}`}
      aria-pressed={active}
      aria-label={`${getVoiceLabel(name)} ${name}`}
      onClick={() => onClick(name)}
    >
      <span className="settings-voice-chip__title">{getVoiceLabel(name)}</span>
      <span className="settings-voice-chip__code">{name}</span>
    </button>
  );
}

export function SettingsPage() {
  const { sensor, refresh: refreshSensor } = useLiveSensor();
  const [isSavingMode, setIsSavingMode] = useState(false);
  const [voiceHealth, setVoiceHealth] = useState<VoiceHealthState>({ names: normalizeVoiceNames(), loaded: false, error: '' });
  const [selectedVoiceName, setSelectedVoiceName] = useState<string>(() => getStoredVoiceName());
  const [personaId, setPersonaId] = useState<PersonaPresetId>(() => getStoredPersonaPreset());
  const [isPersonaDropdownOpen, setIsPersonaDropdownOpen] = useState(false);
  const [isVoiceDropdownOpen, setIsVoiceDropdownOpen] = useState(false);
  const selectedVoiceRef = useRef(selectedVoiceName);

  const webMode = sensor?.runtime_settings?.web_voice_enabled ?? false;
  const notificationIcon = webMode ? '/images/incoming/silent2.png' : '/images/incoming/icon-notification.png';
  const notificationClass = webMode ? 'is-off' : 'is-on';

  const versionIcon = '/images/incoming/list.png';
  const activePersonaIndex = PERSONA_PRESETS.findIndex(p => p.id === personaId);
  const activePersonaNumber = activePersonaIndex >= 0 ? activePersonaIndex + 1 : 1;
  const activePersona = resolvePersonaPreset(personaId);

  useEffect(() => {
    selectedVoiceRef.current = selectedVoiceName;
  }, [selectedVoiceName]);

  const handleToggleWebMode = async () => {
    if (isSavingMode || !sensor?.runtime_settings) return;
    setIsSavingMode(true);
    try {
      const nextWebVoiceEnabled = !sensor.runtime_settings.web_voice_enabled;
      await updateRuntimeSettings({
        web_voice_enabled: nextWebVoiceEnabled,
      });
      await refreshSensor();
    } catch (err) {
      console.error('Failed to update runtime settings:', err);
    } finally {
      setIsSavingMode(false);
    }
  };

  useEffect(() => {
    let active = true;

    const syncVoiceHealth = async () => {
      try {
        const next = await checkVoiceHealth();
        if (!active) return;

        const nextNames = normalizeVoiceNames(next.tts_voice_names);
        const resolvedVoice = resolveVoiceNamePreference(nextNames);
        const safeCurrent = selectedVoiceRef.current.trim().toUpperCase();
        const nextVoice = nextNames.includes(safeCurrent) ? safeCurrent : resolvedVoice;

        setVoiceHealth({
          names: nextNames,
          loaded: true,
          error: '',
        });
        setSelectedVoiceName(nextVoice);
        if (nextVoice !== safeCurrent) {
          setStoredVoiceName(nextVoice);
        }
      } catch (error) {
        if (!active) return;

        const fallbackNames = normalizeVoiceNames();
        const resolved = resolveVoiceNamePreference(fallbackNames);
        const safeCurrent = selectedVoiceRef.current.trim().toUpperCase();
        const nextValue = fallbackNames.includes(safeCurrent) ? safeCurrent : resolved;

        setVoiceHealth({
          names: fallbackNames,
          loaded: true,
          error: error instanceof Error ? error.message : 'TTS 음성 목록을 불러오지 못했습니다.',
        });
        setSelectedVoiceName(nextValue);
        if (nextValue !== safeCurrent) {
          setStoredVoiceName(nextValue);
        }
      }
    };

    void syncVoiceHealth();
    const timer = window.setInterval(() => void syncVoiceHealth(), 15000);
    return () => {
      active = false;
      window.clearInterval(timer);
    };
  }, []);

  const groupedVoices = useMemo(() => groupVoiceNames(voiceHealth.names), [voiceHealth.names]);

  const selectedGroup: VoiceGroup = getVoiceGroup(selectedVoiceName);
  const activeGroupVoices = selectedGroup === 'female' ? groupedVoices.female : groupedVoices.male;
  const activeGroupLabel = selectedGroup === 'female' ? '여자' : '남자';
  const activeGroupImage = selectedGroup === 'female' ? '/images/incoming/female.png' : '/images/incoming/man.png';

  const handleSelectVoice = (name: string) => {
    const nextName = name.trim().toUpperCase();
    setSelectedVoiceName(nextName);
    setStoredVoiceName(nextName);
  };

  const handleToggleGender = (e?: React.MouseEvent) => {
    if (e) {
      e.stopPropagation();
    }
    const nextGroup: VoiceGroup = selectedGroup === 'female' ? 'male' : 'female';
    const nextVoice =
      (nextGroup === 'female' ? groupedVoices.female[0] : groupedVoices.male[0]) ??
      (nextGroup === 'female' ? groupedVoices.male[0] : groupedVoices.female[0]) ??
      selectedVoiceName;

    if (nextVoice) {
      setSelectedVoiceName(nextVoice);
      setStoredVoiceName(nextVoice);
    }
  };

  const handleSelectPersona = (nextPersonaId: PersonaPresetId) => {
    setPersonaId(nextPersonaId);
    setStoredPersonaPreset(nextPersonaId);
  };

  const visiblePersonaItems = PERSONA_PRESETS;

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
              className={`settings-button settings-button--notification ${notificationClass}`}
              onClick={handleToggleWebMode}
              aria-pressed={!webMode}
              disabled={isSavingMode || !sensor?.runtime_settings}
              style={{ position: 'relative', opacity: isSavingMode || !sensor?.runtime_settings ? 0.7 : 1, cursor: isSavingMode || !sensor?.runtime_settings ? 'not-allowed' : 'pointer' }}
            >
              <img className="settings-button__icon" src={notificationIcon} alt="" aria-hidden="true" />
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px', zIndex: 10, position: 'relative' }}>
                <div style={{ width: '18px', flexShrink: 0 }}></div>
                <span className="settings-button__title">{webMode ? '웹' : '로컬'}</span>
                <div style={{ width: '18px', flexShrink: 0 }}></div>
              </div>
            </button>

            <div
              className={`settings-button settings-button--voice ${selectedGroup === 'female' ? 'is-female' : 'is-male'}`}
              style={{ position: 'relative' }}
            >
              <img 
                className="settings-button__icon" 
                src={activeGroupImage} 
                alt="성별 전환" 
                onClick={handleToggleGender}
                style={{ cursor: 'pointer', zIndex: 10, position: 'relative' }}
              />
              <div 
                style={{ display: 'flex', alignItems: 'center', gap: '6px', cursor: 'pointer', zIndex: 10, position: 'relative' }}
                onClick={() => setIsVoiceDropdownOpen(!isVoiceDropdownOpen)}
              >
                <div style={{ width: '18px', flexShrink: 0 }}></div>
                <span className="settings-button__title">{activeGroupLabel}</span>
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#4c3417" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" style={{ flexShrink: 0, transform: isVoiceDropdownOpen ? 'rotate(180deg)' : 'none', transition: 'transform 0.2s' }}>
                  <polyline points="6 9 12 15 18 9"></polyline>
                </svg>
              </div>

              {isVoiceDropdownOpen && (
                <div style={{
                  position: 'absolute',
                  top: '105%',
                  left: '50%',
                  transform: 'translateX(-50%)',
                  width: '240px',
                  background: '#fff',
                  border: '2px solid rgba(139, 94, 36, 0.2)',
                  borderRadius: '16px',
                  padding: '16px',
                  boxShadow: '0 12px 24px rgba(58, 32, 12, 0.15)',
                  zIndex: 20,
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '12px'
                }}>
                  <div style={{ fontSize: '0.9rem', fontWeight: 900, color: '#4c3417', borderBottom: '1px solid #eee', paddingBottom: '8px' }}>
                    {activeGroupLabel} 모델 선택
                  </div>
                  <div className="settings-voice-tabs" style={{ justifyContent: 'center' }}>
                    {activeGroupVoices.length > 0 ? (
                      activeGroupVoices.map((name) => <VoiceChip key={name} name={name} active={selectedVoiceName === name} onClick={handleSelectVoice} />)
                    ) : (
                      <span className="settings-voice-tabs__empty">목소리가 없습니다.</span>
                    )}
                  </div>
                  {groupedVoices.other.length > 0 && (
                    <>
                      <div style={{ fontSize: '0.9rem', fontWeight: 900, color: '#4c3417', borderBottom: '1px solid #eee', paddingBottom: '8px', paddingTop: '8px' }}>기타</div>
                      <div className="settings-voice-tabs" style={{ justifyContent: 'center' }}>
                        {groupedVoices.other.map((name) => (
                          <VoiceChip key={name} name={name} active={selectedVoiceName === name} onClick={handleSelectVoice} />
                        ))}
                      </div>
                    </>
                  )}
                </div>
              )}
            </div>

            <div
              className="settings-button settings-button--persona"
              style={{ position: 'relative' }}
            >
              <img className="settings-button__icon" src={versionIcon} alt="" aria-hidden="true" />
              <div 
                style={{ display: 'flex', alignItems: 'center', gap: '6px', cursor: 'pointer', zIndex: 10, position: 'relative' }}
                onClick={() => setIsPersonaDropdownOpen(!isPersonaDropdownOpen)}
              >
                <div style={{ width: '18px', flexShrink: 0 }}></div>
                <span className="settings-button__title">성격 {activePersonaNumber}</span>
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#4c3417" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" style={{ flexShrink: 0, transform: isPersonaDropdownOpen ? 'rotate(180deg)' : 'none', transition: 'transform 0.2s' }}>
                  <polyline points="6 9 12 15 18 9"></polyline>
                </svg>
              </div>

              {isPersonaDropdownOpen && (
                <div style={{
                  position: 'absolute',
                  top: '105%',
                  left: '50%',
                  transform: 'translateX(-50%)',
                  width: '240px',
                  background: '#fff',
                  border: '2px solid rgba(139, 94, 36, 0.2)',
                  borderRadius: '16px',
                  padding: '16px',
                  boxShadow: '0 12px 24px rgba(58, 32, 12, 0.15)',
                  zIndex: 20,
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '12px'
                }}>
                  <div style={{ fontSize: '0.9rem', fontWeight: 900, color: '#4c3417', borderBottom: '1px solid #eee', paddingBottom: '8px', flexShrink: 0 }}>
                    성격 설정
                  </div>
                  <div className="settings-modal__persona-list" style={{ gap: '8px', maxHeight: '140px', overflowY: 'auto', paddingRight: '4px' }}>
                    {visiblePersonaItems.map((item, index) => {
                      const selected = personaId === item.id;
                      return (
                        <button
                          key={item.id}
                          type="button"
                          className={`settings-modal__persona-item ${selected ? 'is-selected' : ''}`}
                          onClick={() => {
                            handleSelectPersona(item.id);
                            setIsPersonaDropdownOpen(false);
                          }}
                          style={{ padding: '10px 14px', borderRadius: '14px', gap: '4px' }}
                        >
                          <span className="settings-modal__persona-title" style={{ fontSize: '0.88rem' }}>성격 {index + 1} = {item.label}</span>
                          <span className="settings-modal__persona-desc" style={{ fontSize: '0.78rem' }}>{item.description}</span>
                        </button>
                      );
                    })}
                  </div>
                  <div className="settings-modal__current" style={{ marginTop: '4px', fontSize: '0.88rem' }}>
                    현재 선택: <strong>성격 {activePersonaNumber}</strong>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>

        <img className="settings-screen__grass" src="/images/incoming/grass-pattern3-1.png" alt="" aria-hidden="true" />
        <img
          className="settings-screen__grass settings-screen__grass--right"
          src="/images/incoming/grass-pattern3-1.png"
          alt=""
          aria-hidden="true"
        />
      </section>
    </div>
  );
}
