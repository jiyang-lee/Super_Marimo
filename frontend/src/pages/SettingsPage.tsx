import '../styles/settings.css';
import { useEffect, useState } from 'react';
import { MarimoSpeech } from '../components/MarimoSpeech';
import { PixelCard } from '../components/PixelCard';
import { PixelButton } from '../components/PixelButton';
import { getRuntimeSettings, updateRuntimeSettings, type RuntimeSettings } from '../api';

export function SettingsPage() {
  const [settings, setSettings] = useState<RuntimeSettings | null>(null);
  const [error, setError] = useState('');
  const [savingKey, setSavingKey] = useState<string | null>(null);

  const load = async () => {
    try {
      const result = await getRuntimeSettings();
      setSettings(result.settings);
      setError('');
    } catch (e) {
      setError(e instanceof Error ? e.message : '설정을 불러오지 못했습니다.');
    }
  };

  useEffect(() => {
    void load();
  }, []);

  const toggle = async (key: keyof Pick<RuntimeSettings, 'web_voice_enabled' | 'wake_enabled' | 'distance_detection_enabled'>) => {
    if (!settings) return;
    setSavingKey(key);
    try {
      const result = await updateRuntimeSettings({ [key]: !settings[key] });
      setSettings(result.settings);
      setError('');
    } catch (e) {
      setError(e instanceof Error ? e.message : '설정 변경에 실패했습니다.');
    } finally {
      setSavingKey(null);
    }
  };

  const updateDistance = async (value: number) => {
    setSavingKey('distance_threshold_cm');
    try {
      const result = await updateRuntimeSettings({ distance_threshold_cm: value });
      setSettings(result.settings);
      setError('');
    } catch (e) {
      setError(e instanceof Error ? e.message : '거리 기준 변경에 실패했습니다.');
    } finally {
      setSavingKey(null);
    }
  };

  const rows = settings
    ? [
        { key: 'web_voice_enabled' as const, label: '웹 음성 모드', desc: '브라우저 버튼으로 대화 입력을 제어합니다.' },
        { key: 'wake_enabled' as const, label: '호출어 감지', desc: '기기 쪽 호출어 감지 루프를 켭니다.' },
        { key: 'distance_detection_enabled' as const, label: '거리 감지', desc: '거리 센서 기반 자동 반응을 사용합니다.' },
      ]
    : [];

  return (
    <div className="settings-page mx-auto flex max-w-4xl flex-col gap-4">
      <MarimoSpeech text="운영 모드를 여기서 바꿀 수 있어요." />
      {error ? <div className="rounded-lg border border-red-300 bg-red-50 p-3 text-sm text-red-700">{error}</div> : null}
      <PixelCard title="실시간 설정">
        <div className="space-y-3">
          {rows.map((item) => (
            <div key={item.key} className="flex flex-wrap items-center gap-3 rounded-lg border border-bark/10 bg-white/70 p-3">
              <div className="flex-1">
                <div className="font-dot text-sm font-bold text-bark">{item.label}</div>
                <div className="mt-1 text-xs leading-5 text-bark/60">{item.desc}</div>
              </div>
              <PixelButton
                type="button"
                size="sm"
                variant={settings?.[item.key] ? 'green' : 'gold'}
                disabled={savingKey === item.key}
                onClick={() => void toggle(item.key)}
              >
                {settings?.[item.key] ? 'ON' : 'OFF'}
              </PixelButton>
            </div>
          ))}
          <label className="block rounded-lg border border-bark/10 bg-white/70 p-3">
            <div className="flex items-center justify-between gap-3">
              <span className="font-dot text-sm font-bold text-bark">거리 기준</span>
              <span className="font-dot text-xs text-bark/60">{settings?.distance_threshold_cm ?? '-'} cm</span>
            </div>
            <input
              type="range"
              min="5"
              max="120"
              value={settings?.distance_threshold_cm ?? 30}
              disabled={!settings || savingKey === 'distance_threshold_cm'}
              onChange={(event) => void updateDistance(Number(event.target.value))}
              className="mt-3 w-full accent-sky"
            />
          </label>
        </div>
      </PixelCard>
    </div>
  );
}
