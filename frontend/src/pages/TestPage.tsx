import { useEffect, useMemo, useState } from 'react';
import { askChat, getLatestSensor, getRuntimeSettings, getRuntimeSettingsHistory, synthesizeTts, updateRuntimeSettings, type AskResult, type RuntimeSettings, type RuntimeSettingsHistory, type SensorLatest } from '../api';

const QUICK_PROMPTS = [
  {
    label: '거리 감지 켜줘',
    prompt: 'distance detection on',
    tone: 'border-sky bg-sky/15 text-sky',
    badge: '감지 켜기',
  },
  {
    label: '거리 감지 꺼줘',
    prompt: 'distance detection off',
    tone: 'border-rose-500 bg-rose-500/15 text-rose-600',
    badge: '감지 끄기',
  },
  {
    label: '지금 상태 알려줘',
    prompt: 'SENSOR_STATUS_TRIGGER',
    tone: 'border-emerald-500 bg-emerald-500/15 text-emerald-700',
    badge: '센서값 전송',
  },
] as const;

export function sanitizeMessageContent(content: string): string {
  if (!content) return '';
  const trimmed = content.trim();
  
  // 마크다운 코드블록 json 이 씌워져 있다면 1차 세척
  let target = trimmed;
  if (target.includes('```')) {
    target = target.replace(/```(?:json)?/gi, '').trim();
  }
  // 끝부분에 이상한 마크다운 기호(예: **)가 붙어있으면 제거
  target = target.replace(/\s*\*+\s*$/, '').trim();

  // JSON 오브젝트 형태로 보이는 부분만 추출 시도 (중괄호 { } 찾기)
  const jsonStart = target.indexOf('{');
  const jsonEnd = target.lastIndexOf('}');
  if (jsonStart !== -1) {
    let jsonContent = target;
    if (jsonEnd > jsonStart) {
      jsonContent = target.slice(jsonStart, jsonEnd + 1);
    } else {
      jsonContent = target.slice(jsonStart);
    }
    
    // 1. 완벽한 JSON 파싱 시도
    try {
      const parsed = JSON.parse(jsonContent);
      if (parsed && typeof parsed === 'object') {
        const candidateKeys = ['answer', 'answe', 'answ', 'llm_answer', 'response', 'text'];
        for (const key of candidateKeys) {
          if (key in parsed) {
            return String(parsed[key]);
          }
        }
      }
    } catch {
      // 2. 파싱이 깨진 경우 정규식으로 유연하게 추출
      // answe, answer, llm_answer, answ, response 등 오타 대응
      const match = jsonContent.match(/"(?:answer|answe|answ|llm_answer|response|text)"\s*:\s*"([^"\\]*(?:\\.[^"\\]*)*)"/si);
      if (match) {
        try {
          return JSON.parse(`"${match[1]}"`);
        } catch {
          return match[1];
        }
      }
      
      const simpleMatch = jsonContent.match(/"(?:answer|answe|answ|llm_answer|response|text)"\s*:\s*"(.*?)"/si);
      if (simpleMatch) {
        return simpleMatch[1];
      }
    }
  }
  
  return target;
}

function yesNo(value?: boolean) {
  if (value === undefined) return '-';
  return value ? '켜짐' : '꺼짐';
}

function statusText(sensor: SensorLatest | null) {
  const hasData = !!sensor?.latest_merged;
  if (hasData) {
    return { label: '연결됨', tone: 'bg-emerald-500/15 text-emerald-700 border-emerald-500' };
  }
  return { label: '대기 중', tone: 'bg-slate-500/15 text-slate-600 border-slate-400' };
}

function summarizeAnswer(result: AskResult | null) {
  const action = result?.action_result?.summary?.trim();
  const rawAnswer = result?.llm_answer?.trim() || result?.answer?.trim();
  const answer = rawAnswer ? sanitizeMessageContent(rawAnswer) : '';
  if (action && answer) return `${action} / ${answer}`;
  return action || answer || '아직 실행한 결과가 없어요.';
}

export function TestPage() {
  const [sensor, setSensor] = useState<SensorLatest | null>(null);
  const [settings, setSettings] = useState<RuntimeSettings | null>(null);
  const [input, setInput] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [sessionId, setSessionId] = useState<string | undefined>(undefined);
  const [lastResult, setLastResult] = useState<AskResult | null>(null);
  const [lastCheckedAt, setLastCheckedAt] = useState('');
  const [history, setHistory] = useState<RuntimeSettingsHistory[]>([]);
  const [updatingMode, setUpdatingMode] = useState(false);

  const handleModeChange = async (webVoiceEnabled: boolean) => {
    if (updatingMode || !settings) return;
    setUpdatingMode(true);
    setError('');
    try {
      const res = await updateRuntimeSettings({ web_voice_enabled: webVoiceEnabled });
      setSettings(res.settings);
      await refreshBoard();
    } catch (e) {
      setError(e instanceof Error ? e.message : '구동 모드 변경에 실패했어요.');
    } finally {
      setUpdatingMode(false);
    }
  };

  const refreshBoard = async () => {
    const [nextSensor, nextSettings, nextHistory] = await Promise.all([
      getLatestSensor(),
      getRuntimeSettings(),
      getRuntimeSettingsHistory(5),
    ]);
    setSensor(nextSensor);
    setSettings(nextSettings.settings);
    setHistory(nextHistory.history);
    setLastCheckedAt(new Date().toLocaleTimeString('ko-KR'));
  };

  useEffect(() => {
    void refreshBoard().catch((e) => setError(e instanceof Error ? e.message : 'refresh failed'));

    // 기기 단독 구동 모드에서 음성 명령 등으로 설정이 바뀌는 것을 실시간(3초 주기)으로 감지해 반영합니다.
    const timer = setInterval(() => {
      void refreshBoard().catch(() => {});
    }, 3000);

    return () => clearInterval(timer);
  }, []);

  const status = useMemo(() => statusText(sensor), [sensor]);
  const merged = sensor?.latest_merged ?? null;
  const actionSummary = useMemo(() => summarizeAnswer(lastResult), [lastResult]);

  const send = async (text: string) => {
    const value = text.trim();
    if (!value || busy) return;
    setBusy(true);
    setError('');
    try {
      const result = await askChat(value, sessionId, true);
      setLastResult(result);
      setSessionId(result.session_id);
      setInput('');
      await refreshBoard();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'send failed');
    } finally {
      setBusy(false);
    }
  };

  const playLast = async () => {
    const rawText = lastResult?.tts_text || lastResult?.llm_answer || lastResult?.answer || '';
    const text = sanitizeMessageContent(rawText);
    if (!text) return;
    try {
      const blob = await synthesizeTts(text);
      const url = URL.createObjectURL(blob);
      const audio = new Audio(url);
      audio.onended = () => URL.revokeObjectURL(url);
      await audio.play();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'tts failed');
    }
  };

  return (
    <div className="mx-auto flex max-w-6xl flex-col gap-5">
      <section className="overflow-hidden rounded-[2rem] border-4 border-bark/15 bg-white/80 shadow-[0_18px_0_rgba(15,23,42,0.06)]">
        <div className="grid gap-4 p-5 md:grid-cols-[1.4fr_1fr] md:p-7">
          <div className="flex flex-col gap-4">
            <div className="inline-flex w-fit rounded-full border-2 border-sky bg-sky/15 px-4 py-1 font-dot text-xs text-sky">
              놀이방 테스트 페이지
            </div>
            <div className="space-y-2">
              <h1 className="text-4xl font-black tracking-tight text-bark md:text-6xl">마리모 놀이방</h1>
              <p className="max-w-2xl text-base leading-7 text-bark/70 md:text-lg">
                큰 버튼을 누르면 마리모가 상태를 보고, 안전한 설정을 바꾸고, 바뀐 결과를 바로 보여줘요.
              </p>
            </div>

            {/* 에이전트 구동 모드 토글 카드 */}
            <div className="mt-1 grid gap-4 sm:grid-cols-2">
              <button
                type="button"
                onClick={() => void handleModeChange(true)}
                disabled={updatingMode}
                className={[
                  'relative group rounded-[1.8rem] border-4 p-4 text-left transition-all active:scale-[0.98] duration-150',
                  settings?.web_voice_enabled === true
                    ? 'border-sky bg-sky/10 shadow-[0_8px_0_rgba(14,165,233,0.15)] ring-4 ring-sky/10'
                    : 'border-bark/10 bg-white/40 hover:bg-white/70 opacity-80'
                ].join(' ')}
              >
                <div className="flex items-center justify-between">
                  <span className={`font-dot text-xs font-bold ${settings?.web_voice_enabled === true ? 'text-sky' : 'text-bark/40'}`}>
                    MODE 01
                  </span>
                  {settings?.web_voice_enabled === true && (
                    <span className="rounded-full bg-sky px-2 py-0.5 font-dot text-[9px] text-white animate-pulse">ON</span>
                  )}
                </div>
                <div className={`mt-1.5 text-xl font-black ${settings?.web_voice_enabled === true ? 'text-sky-900' : 'text-bark/80'}`}>
                  웹 음성 대화 모드
                </div>
                <p className="mt-1 text-xs leading-relaxed text-bark/60">
                  웹 페이지의 버튼(마이크 버튼 및 퀵 버튼)을 눌러 브라우저 마이크/스피커로 마리모와 실시간 대화를 나눕니다. (호출어 감지 OFF)
                </p>
              </button>

              <button
                type="button"
                onClick={() => void handleModeChange(false)}
                disabled={updatingMode}
                className={[
                  'relative group rounded-[1.8rem] border-4 p-4 text-left transition-all active:scale-[0.98] duration-150',
                  settings?.web_voice_enabled === false
                    ? 'border-emerald-500 bg-emerald-500/10 shadow-[0_8px_0_rgba(16,185,129,0.15)] ring-4 ring-emerald-500/10'
                    : 'border-bark/10 bg-white/40 hover:bg-white/70 opacity-80'
                ].join(' ')}
              >
                <div className="flex items-center justify-between">
                  <span className={`font-dot text-xs font-bold ${settings?.web_voice_enabled === false ? 'text-emerald-600' : 'text-bark/40'}`}>
                    MODE 02
                  </span>
                  {settings?.web_voice_enabled === false && (
                    <span className="rounded-full bg-emerald-500 px-2 py-0.5 font-dot text-[9px] text-white animate-pulse">ON</span>
                  )}
                </div>
                <div className={`mt-1.5 text-xl font-black ${settings?.web_voice_enabled === false ? 'text-emerald-900' : 'text-bark/80'}`}>
                  기기 단독 구동 모드
                </div>
                <p className="mt-1 text-xs leading-relaxed text-bark/60">
                  웹 브라우저의 버튼 없이, 기기 자체에서 직접 호출어("마리모야")를 감지하여 하드웨어 단독으로 음성 대화와 센서를 제어합니다. (호출어 감지 ON)
                </p>
              </button>
            </div>

            <div className="grid gap-3 sm:grid-cols-3">
              <div className="rounded-3xl border-4 border-emerald-500 bg-emerald-500/10 p-4">
                <div className="font-dot text-sm text-emerald-700">센서 연결</div>
                <div className="mt-2 text-3xl font-black text-emerald-800">{status.label}</div>
              </div>
              <div className="rounded-3xl border-4 border-sky bg-sky/10 p-4">
                <div className="font-dot text-sm text-sky">지금 설정</div>
                <div className="mt-2 text-3xl font-black text-sky">
                  {yesNo(settings?.distance_detection_enabled)}
                </div>
              </div>
              <div className="rounded-3xl border-4 border-amber-500 bg-amber-500/10 p-4">
                <div className="font-dot text-sm text-amber-700">마지막 결과</div>
                <div className="mt-2 text-3xl font-black text-amber-800">{lastResult ? '완료' : '대기'}</div>
              </div>
            </div>
          </div>

          <div className="flex flex-col justify-between gap-3 rounded-[1.5rem] bg-[linear-gradient(180deg,#fff6d8_0%,#fffdf4_100%)] p-5">
            <div>
              <div className="font-dot text-sm uppercase tracking-[0.3em] text-bark/50">Quick Check</div>
              <div className="mt-2 text-2xl font-black text-bark">실시간 센서 정보</div>
              <p className="mt-2 text-sm leading-6 text-bark/70">
                기기 및 센서가 전송하는 현재 실시간 환경 정보 값입니다.
              </p>
            </div>

            <div className="rounded-[1.25rem] border-4 border-bark/15 bg-white/90 p-4">
              <div className="font-dot text-xs text-bark/50 mb-3">현재 수신된 센서 값</div>
              <div className="grid grid-cols-3 gap-2 text-center">
                <div className="rounded-xl bg-bark/5 p-2 border border-bark/10">
                  <div className="text-[10px] font-bold text-bark/50">기온</div>
                  <div className="text-lg font-black text-bark">{merged?.temperature ?? '-'}°C</div>
                </div>
                <div className="rounded-xl bg-bark/5 p-2 border border-bark/10">
                  <div className="text-[10px] font-bold text-bark/50">거리</div>
                  <div className="text-lg font-black text-bark">{merged?.distance ?? '-'}cm</div>
                </div>
                <div className="rounded-xl bg-bark/5 p-2 border border-bark/10">
                  <div className="text-[10px] font-bold text-bark/50">물높이</div>
                  <div className="text-lg font-black text-bark">{merged?.water_level ?? '-'}</div>
                </div>
              </div>
              <div className="mt-3 text-[10px] font-dot text-bark/40 text-center">
                {merged ? '데이터가 정상적으로 수신 중입니다.' : '센서 데이터 수신 대기 중...'}
              </div>
            </div>
          </div>
        </div>
      </section>

      {error && (
        <div className="rounded-[1.5rem] border-4 border-rose-500 bg-rose-500/10 p-4 text-base font-bold text-rose-700">
          {error}
        </div>
      )}

      <section className="grid gap-4 lg:grid-cols-[1.3fr_0.9fr]">
        <div className="rounded-[2rem] border-4 border-bark/15 bg-white/80 p-5 shadow-[0_14px_0_rgba(15,23,42,0.04)]">
          <div className="flex items-center justify-between gap-3">
            <h2 className="text-2xl font-black text-bark">버튼으로 해보기</h2>
            <span className="rounded-full border-2 border-bark/15 bg-white px-3 py-1 font-dot text-xs text-bark/50">
              {lastCheckedAt ? `새로고침 ${lastCheckedAt}` : '아직 확인 전'}
            </span>
          </div>

          <div className="mt-4 grid gap-3 sm:grid-cols-2">
            {QUICK_PROMPTS.map((item) => (
              <button
                key={item.prompt}
                type="button"
                onClick={() => {
                  if (item.prompt === 'SENSOR_STATUS_TRIGGER') {
                    const temp = merged?.temperature ?? '-';
                    const dist = merged?.distance ?? '-';
                    const water = merged?.water_level ?? '-';
                    void send(`현재 센서 상태: 기온 ${temp}도, 거리 ${dist}cm, 물높이 ${water}`);
                  } else {
                    void send(item.prompt);
                  }
                }}
                disabled={busy}
                className={[
                  'group rounded-[1.5rem] border-4 px-4 py-5 text-left transition active:scale-[0.99] disabled:opacity-60',
                  item.tone,
                ].join(' ')}
              >
                <div className="flex items-center justify-between gap-3">
                  <div className="text-2xl font-black">{item.label}</div>
                  <span className="rounded-full bg-white/80 px-3 py-1 font-dot text-xs text-bark">{item.badge}</span>
                </div>
                <div className="mt-2 text-sm leading-6 text-bark/70">
                  누르면 마리모가 바로 알아듣고, 결과도 보여줘요.
                </div>
              </button>
            ))}
          </div>

          <div className="mt-5 rounded-[1.5rem] border-4 border-bark/10 bg-white/70 p-4">
            <div className="font-dot text-sm text-bark/60">직접 쓰기</div>
            <div className="mt-3 flex flex-col gap-3 sm:flex-row">
              <input
                className="min-h-14 flex-1 rounded-[1.2rem] border-4 border-bark/20 bg-white px-4 py-3 text-lg font-bold text-bark outline-none transition focus:border-sky"
                value={input}
                onChange={(event) => setInput(event.target.value)}
                onKeyDown={(event) => {
                  if (event.key === 'Enter') void send(input);
                }}
                placeholder="예: 거리 감지 꺼줘"
                disabled={busy}
              />
              <button
                type="button"
                onClick={() => void send(input)}
                disabled={busy}
                className="min-h-14 rounded-[1.2rem] border-4 border-bark bg-bark px-6 py-3 text-lg font-black text-white transition hover:scale-[1.01] disabled:opacity-60"
              >
                {busy ? '보내는 중...' : '보내기'}
              </button>
            </div>
          </div>
        </div>

        <div className="flex flex-col gap-4">
          <div className="rounded-[2rem] border-4 border-sky/20 bg-sky/10 p-5">
            <div className="flex items-center justify-between gap-3">
              <h2 className="text-2xl font-black text-bark">마지막 결과</h2>
              <button
                type="button"
                onClick={() => void playLast()}
                disabled={!lastResult}
                className="rounded-full border-4 border-sky bg-white px-4 py-2 font-black text-sky disabled:opacity-50"
              >
                말로 듣기
              </button>
            </div>
            <div className="mt-4 rounded-[1.4rem] border-4 border-white bg-white/90 p-4">
              <div className="text-xl font-black text-bark">{actionSummary}</div>
              <div className="mt-3 space-y-2 text-sm leading-6 text-bark/70">
                <p>성공하면 설정이 바뀌고, 실패하면 이유가 보여요.</p>
                <p>이 화면에서는 긴 글보다 “무엇이 바뀌었는지”를 먼저 보여줘요.</p>
              </div>
            </div>
          </div>

          <div className="rounded-[2rem] border-4 border-emerald-500/20 bg-emerald-500/10 p-5">
            <h2 className="text-2xl font-black text-bark">지금 설정</h2>
            <div className="mt-4 grid grid-cols-2 gap-3">
              {[
                { label: '거리 감지', value: yesNo(settings?.distance_detection_enabled) },
                { label: '깨우기', value: yesNo(settings?.wake_enabled) },
                { label: '웹 음성', value: yesNo(settings?.web_voice_enabled) },
                { label: '기준', value: settings ? `${settings.distance_threshold_cm}cm` : '-' },
              ].map((item) => (
                <div key={item.label} className="rounded-[1.2rem] border-4 border-white bg-white p-4">
                  <div className="font-dot text-sm text-bark/50">{item.label}</div>
                  <div className="mt-1 text-2xl font-black text-bark">{item.value}</div>
                </div>
              ))}
            </div>
          </div>

          <div className="rounded-[2rem] border-4 border-bark/15 bg-white/80 p-5">
            <h2 className="text-2xl font-black text-bark">최근 설정 변경</h2>
            <div className="mt-4 space-y-2">
              {history.length === 0 && (
                <div className="font-dot text-sm text-bark/50">아직 변경 이력이 없어요.</div>
              )}
              {history.map((h) => (
                <div key={h.history_id} className="rounded-[1.2rem] border-4 border-white bg-white p-3">
                  <div className="font-dot text-xs text-bark/50">
                    {new Date(h.changed_at).toLocaleString('ko-KR')}
                  </div>
                  <div className="mt-1 text-sm font-bold text-bark">
                    {h.summary || '설정이 바뀌었어요.'}
                  </div>
                  <div className="font-dot text-[10px] text-bark/40">
                    {h.changed_by ? `session ${h.changed_by.slice(0, 8)}` : 'system'}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>
    </div>
  );
}
