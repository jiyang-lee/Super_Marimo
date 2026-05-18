import { useEffect, useMemo, useRef, useState } from 'react';
import {
  askAgent,
  checkAgentHealth,
  checkApiHealth,
  checkLlmHealth,
  checkVoiceHealth,
  getLatestSensor,
  getSessionDetail,
  listSessions,
  synthesizeTts,
  type AgentHealth,
  type ApiHealth,
  type AskResult,
  type LlmHealth,
  type SensorLatest,
  type SessionDetail,
  type SessionSummary,
  type VoiceHealth,
} from './api';

type ServiceState = {
  label: string;
  ok: boolean;
  detail: string;
};

type ChatMessage = {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  createdAt: string;
};

const DEFAULT_SYSTEM_MEMO = '한국어만 사용하고, 1~2문장으로 짧고 자연스럽게 답한다.';

const PERSONA_PRESETS = [
  {
    id: 'kid',
    label: '꼬마 기본',
    memo:
      '한국인 꼬마 같은 말투를 쓰되 예의 바르고 다정하게 말한다. 짧고 자연스럽게 답하고, 너무 유치하지 않게 부드러운 톤을 유지한다.',
  },
  {
    id: 'bright',
    label: '밝은 꼬마',
    memo:
      '밝고 명랑한 한국인 꼬마 느낌으로 말하되 예의 바르고 친절하게 답한다. 짧고 자연스럽게 핵심만 말한다.',
  },
  {
    id: 'calm',
    label: '차분한 꼬마',
    memo:
      '차분한 한국인 꼬마 느낌으로 말하되 예의 바르고 부드럽게 답한다. 짧고 자연스럽게 핵심만 말한다.',
  },
  {
    id: 'custom',
    label: '직접 입력',
    memo: '',
  },
] as const;

function formatDateTime(value: string | null | undefined): string {
  if (!value) return 'none';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat('ko-KR', {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(date);
}

function toneClass(ok: boolean, tone: 'neutral' | 'green' | 'amber' | 'rose' = 'neutral') {
  const palette: Record<'neutral' | 'green' | 'amber' | 'rose', string> = {
    neutral: 'border-fuchsia-300/20 bg-white/10 text-white',
    green: 'border-emerald-300/40 bg-emerald-400/20 text-emerald-50',
    amber: 'border-amber-300/40 bg-amber-400/20 text-amber-50',
    rose: 'border-rose-300/40 bg-rose-400/20 text-rose-50',
  };
  return [
    'inline-flex items-center rounded-full border px-3 py-1 text-[11px] font-semibold tracking-[0.22em] uppercase',
    ok ? palette[tone] : 'border-white/10 bg-white/10 text-slate-300',
  ].join(' ');
}

function statusTone(ok: boolean): 'green' | 'amber' | 'rose' {
  return ok ? 'green' : 'rose';
}

function levelTone(level?: string | null): 'green' | 'amber' | 'rose' {
  if (level === 'danger') return 'rose';
  if (level === 'warning') return 'amber';
  return 'green';
}

function StatTile({
  title,
  value,
  helper,
  ok = true,
}: {
  title: string;
  value: string;
  helper: string;
  ok?: boolean;
}) {
  return (
    <div className="rounded-[24px] border border-white/15 bg-white/10 p-4 shadow-[0_16px_50px_rgba(255,255,255,.04)] backdrop-blur">
      <div className="flex items-center justify-between gap-3">
        <div>
          <div className="text-sm font-semibold text-white">{title}</div>
          <div className="mt-1 text-xs text-slate-100/70">{helper}</div>
        </div>
        <span className={toneClass(ok, statusTone(ok))}>{ok ? 'OK' : 'CHECK'}</span>
      </div>
      <div className="mt-4 text-lg font-semibold text-white">{value}</div>
    </div>
  );
}

function SensorMetric({
  label,
  value,
  suffix,
}: {
  label: string;
  value: number | string | null | undefined;
  suffix?: string;
}) {
  const text = value === null || value === undefined || value === '' ? 'none' : `${value}${suffix ?? ''}`;
  return (
    <div className="rounded-[22px] border border-white/15 bg-white/10 p-4 backdrop-blur">
      <div className="text-[11px] uppercase tracking-[0.3em] text-white/55">{label}</div>
      <div className="mt-2 text-lg font-semibold text-white">{text}</div>
    </div>
  );
}

function SessionRow({
  session,
  active,
  onSelect,
}: {
  session: SessionSummary;
  active: boolean;
  onSelect: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onSelect}
      className={[
        'w-full rounded-[22px] border p-4 text-left transition',
        active
          ? 'border-white/40 bg-white/20 shadow-[0_20px_50px_rgba(236,72,153,.2)]'
          : 'border-white/10 bg-white/10 hover:border-white/25 hover:bg-white/15',
      ].join(' ')}
    >
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0">
          <div className="truncate text-sm font-semibold text-white">{session.title || 'new session'}</div>
          <div className="mt-1 overflow-hidden text-sm text-white/75">{session.preview || 'no preview'}</div>
        </div>
        <div className="flex shrink-0 flex-col items-end gap-2">
          <span className={toneClass(Boolean(session.ended_at), session.ended_at ? 'amber' : 'green')}>
            {session.ended_at ? 'ENDED' : 'LIVE'}
          </span>
          <span className="text-xs text-white/60">{session.message_count} msgs</span>
        </div>
      </div>
      <div className="mt-4 grid gap-2 text-xs text-white/60 sm:grid-cols-3">
        <span>{formatDateTime(session.last_seen_at)}</span>
        <span>turn {session.turn_count}</span>
        <span>id {session.session_id.slice(0, 8)}</span>
      </div>
    </button>
  );
}

function MessageBubble({
  role,
  content,
  createdAt,
}: {
  role: string;
  content: string;
  createdAt: string;
}) {
  const isUser = role === 'user';
  const bubbleClass = isUser
    ? 'border-sky-200/30 bg-sky-300/20 text-white'
    : 'border-pink-200/30 bg-pink-300/20 text-white';

  return (
    <article className={['rounded-[22px] border p-4 shadow-[0_10px_30px_rgba(0,0,0,.12)]', bubbleClass].join(' ')}>
      <div className="flex items-center justify-between gap-4 text-[11px] uppercase tracking-[0.28em]">
        <span>{role}</span>
        <span className="text-white/60">{formatDateTime(createdAt)}</span>
      </div>
      <p className="mt-3 whitespace-pre-wrap text-sm leading-7">{content}</p>
    </article>
  );
}

function App() {
  const [agent, setAgent] = useState<AgentHealth | null>(null);
  const [api, setApi] = useState<ApiHealth | null>(null);
  const [voice, setVoice] = useState<VoiceHealth | null>(null);
  const [llm, setLlm] = useState<LlmHealth | null>(null);
  const [sessions, setSessions] = useState<SessionSummary[]>([]);
  const [selectedSessionId, setSelectedSessionId] = useState<string | null>(null);
  const [selectedSession, setSelectedSession] = useState<SessionDetail | null>(null);
  const [sensor, setSensor] = useState<SensorLatest | null>(null);
  const [globalError, setGlobalError] = useState('');
  const [sessionError, setSessionError] = useState('');
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [syncedAt, setSyncedAt] = useState('');
  const [selectedPersonaId, setSelectedPersonaId] = useState<(typeof PERSONA_PRESETS)[number]['id']>('kid');
  const [customPersonaMemo, setCustomPersonaMemo] = useState('');
  const [selectedVoiceName, setSelectedVoiceName] = useState('');
  const [draftQuestion, setDraftQuestion] = useState('');
  const [isSending, setIsSending] = useState(false);
  const [isListening, setIsListening] = useState(false);
  const [askError, setAskError] = useState('');
  const [lastAskResult, setLastAskResult] = useState<AskResult | null>(null);
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([]);
  const [autoSpeak, setAutoSpeak] = useState(true);
  const recognitionRef = useRef<any>(null);
  const chatScrollRef = useRef<HTMLDivElement | null>(null);

  const refreshOverview = async () => {
    setIsRefreshing(true);
    setGlobalError('');
    try {
      const [agentHealth, apiHealth, voiceHealth, llmHealth, sessionList, latestSensor] = await Promise.all([
        checkAgentHealth(),
        checkApiHealth(),
        checkVoiceHealth(),
        checkLlmHealth(),
        listSessions(12),
        getLatestSensor(),
      ]);

      setAgent(agentHealth);
      setApi(apiHealth);
      setVoice(voiceHealth);
      setLlm(llmHealth);
      setSessions(sessionList);
      setSensor(latestSensor);
      setSyncedAt(
        new Date().toLocaleTimeString('ko-KR', {
          hour: '2-digit',
          minute: '2-digit',
          second: '2-digit',
          hour12: false,
        }),
      );
    } catch (error) {
      setGlobalError(error instanceof Error ? error.message : 'overview refresh failed');
    } finally {
      setIsRefreshing(false);
    }
  };

  useEffect(() => {
    void refreshOverview();
    const timer = window.setInterval(() => {
      void refreshOverview();
    }, 10000);
    return () => window.clearInterval(timer);
  }, []);

  useEffect(() => {
    if (!sessions.length) {
      setSelectedSessionId(null);
      return;
    }

    setSelectedSessionId((current) => {
      if (current && sessions.some((item) => item.session_id === current)) {
        return current;
      }
      return sessions[0].session_id;
    });
  }, [sessions]);

  useEffect(() => {
    if (!selectedSessionId) {
      setSelectedSession(null);
      return;
    }

    let alive = true;
    const loadSession = async () => {
      setSessionError('');
      try {
        const detail = await getSessionDetail(selectedSessionId);
        if (alive) {
          setSelectedSession(detail);
        }
      } catch (error) {
        if (alive) {
          setSelectedSession(null);
          setSessionError(error instanceof Error ? error.message : 'session detail load failed');
        }
      }
    };

    void loadSession();
    const timer = window.setInterval(() => {
      void loadSession();
    }, 10000);

    return () => {
      alive = false;
      window.clearInterval(timer);
    };
  }, [selectedSessionId]);

  useEffect(() => {
    const voiceOptions = voice?.tts_voice_names ?? [];
    const fallback = [voice?.tts_runtime_voice_name, voice?.tts_voice_name].filter(
      (value): value is string => Boolean(value),
    );
    const candidates = Array.from(new Set([...voiceOptions, ...fallback]));
    if (!candidates.length) {
      return;
    }

    setSelectedVoiceName((current) => {
      if (current && candidates.includes(current)) {
        return current;
      }
      return candidates[0];
    });
  }, [voice]);

  useEffect(() => {
    chatScrollRef.current?.scrollTo({ top: chatScrollRef.current.scrollHeight, behavior: 'smooth' });
  }, [chatMessages]);

  const selectedPersonaMemo = useMemo(() => {
    if (selectedPersonaId === 'custom') {
      return customPersonaMemo.trim();
    }
    return PERSONA_PRESETS.find((item) => item.id === selectedPersonaId)?.memo ?? PERSONA_PRESETS[0].memo;
  }, [customPersonaMemo, selectedPersonaId]);

  const selectedPersonaLabel = useMemo(() => {
    return PERSONA_PRESETS.find((item) => item.id === selectedPersonaId)?.label ?? '꼬마 기본';
  }, [selectedPersonaId]);

  const voiceOptions = useMemo(() => {
    const names = voice?.tts_voice_names ?? [];
    const fallback = [voice?.tts_runtime_voice_name, voice?.tts_voice_name].filter(
      (value): value is string => Boolean(value),
    );
    return Array.from(new Set([...names, ...fallback]));
  }, [voice]);

  const services = useMemo<ServiceState[]>(() => {
    return [
      {
        label: 'voice-agent',
        ok: Boolean(agent?.ok),
        detail: agent ? `session ${agent.session_id ?? 'none'} | STT ${agent.default_stt_model}` : 'loading',
      },
      {
        label: 'api-server',
        ok: Boolean(api?.ok),
        detail: api ? `DB ${api.db?.ok ? 'connected' : 'check'} | ${api.llm_server_url}` : 'loading',
      },
      {
        label: 'voice-server',
        ok: Boolean(voice?.ok),
        detail: voice ? `TTS ${voice.tts_backend} | ${voice.tts_voice_name}` : 'loading',
      },
      {
        label: 'llm-server',
        ok: Boolean(llm?.ok),
        detail: llm ? `${llm.model} | ${llm.mode}` : 'loading',
      },
    ];
  }, [agent, api, voice, llm]);

  const latestMerged = sensor?.latest_merged ?? null;
  const latestRealtime = sensor?.latest_realtime ?? null;
  const latestHourly = sensor?.latest_hourly ?? null;
  const selectedSessionIndex = selectedSessionId ? sessions.findIndex((item) => item.session_id === selectedSessionId) : -1;
  const overallOk = services.length > 0 && services.every((item) => item.ok);
  const selectedVoiceResolved = selectedVoiceName || voice?.tts_runtime_voice_name || voice?.tts_voice_name || '';

  const playVoice = async (text: string) => {
    if (!text.trim() || !selectedVoiceResolved) {
      return;
    }

    const audioBlob = await synthesizeTts(text, selectedVoiceResolved);
    const audioUrl = URL.createObjectURL(audioBlob);
    const audio = new Audio(audioUrl);
    try {
      await audio.play();
    } finally {
      audio.onended = () => URL.revokeObjectURL(audioUrl);
    }
  };

  const sendQuestion = async (textInput?: string) => {
    const text = (textInput ?? draftQuestion).trim();
    if (!text || isSending) {
      return;
    }

    setIsSending(true);
    setAskError('');

    const now = new Date().toISOString();
    setChatMessages((prev) => [...prev, { id: `${now}-user`, role: 'user', content: text, createdAt: now }]);

    try {
      const result = await askAgent(text, selectedSessionId ?? undefined, {
        personaMemo: selectedPersonaMemo || PERSONA_PRESETS[0].memo,
        systemMemo: DEFAULT_SYSTEM_MEMO,
        voiceName: selectedVoiceResolved || undefined,
        speak: false,
      });

      const answer = result.answer || '';
      setLastAskResult(result);
      setSelectedSessionId(result.session_id);
      setChatMessages((prev) => [
        ...prev,
        {
          id: `${result.session_id}-${Date.now()}-assistant`,
          role: 'assistant',
          content: answer,
          createdAt: new Date().toISOString(),
        },
      ]);

      if (autoSpeak && answer) {
        await playVoice(answer);
      }

      setDraftQuestion('');
      await refreshOverview();
    } catch (error) {
      setAskError(error instanceof Error ? error.message : 'ask failed');
    } finally {
      setIsSending(false);
    }
  };

  const stopRecognition = () => {
    const recognition = recognitionRef.current;
    if (recognition) {
      recognition.stop?.();
      recognitionRef.current = null;
    }
    setIsListening(false);
  };

  const startRecognition = () => {
    setAskError('');
    const SpeechRecognitionCtor =
      (window as unknown as { SpeechRecognition?: any; webkitSpeechRecognition?: any }).SpeechRecognition ||
      (window as unknown as { SpeechRecognition?: any; webkitSpeechRecognition?: any }).webkitSpeechRecognition;

    if (!SpeechRecognitionCtor) {
      setAskError('이 브라우저는 음성 인식을 지원하지 않아요.');
      return;
    }

    if (isListening) {
      stopRecognition();
      return;
    }

    const recognition = new SpeechRecognitionCtor();
    recognition.lang = 'ko-KR';
    recognition.interimResults = false;
    recognition.continuous = false;
    recognition.maxAlternatives = 1;

    recognition.onresult = (event: any) => {
      const transcript = Array.from(event.results)
        .slice(event.resultIndex)
        .map((result: any) => result[0]?.transcript ?? '')
        .join(' ')
        .trim();

      if (transcript) {
        void sendQuestion(transcript);
      }
    };

    recognition.onerror = (event: any) => {
      setAskError(event?.error ? `음성 인식 오류: ${event.error}` : '음성 인식 오류가 발생했어요.');
      setIsListening(false);
    };

    recognition.onend = () => {
      setIsListening(false);
      recognitionRef.current = null;
    };

    recognitionRef.current = recognition;
    setIsListening(true);
    recognition.start();
  };

  return (
    <div className="min-h-screen overflow-hidden bg-[radial-gradient(circle_at_top_left,_rgba(255,192,203,.25),_transparent_30%),radial-gradient(circle_at_top_right,_rgba(103,232,249,.22),_transparent_28%),radial-gradient(circle_at_bottom_left,_rgba(167,243,208,.18),_transparent_30%),linear-gradient(135deg,_#fff7fc_0%,_#ecfeff_40%,_#f5f3ff_100%)] text-slate-800">
      <div className="absolute inset-0 opacity-70">
        <div className="absolute left-[-8rem] top-10 h-72 w-72 rounded-full bg-fuchsia-300/25 blur-3xl" />
        <div className="absolute right-0 top-24 h-80 w-80 rounded-full bg-cyan-300/25 blur-3xl" />
        <div className="absolute bottom-0 left-1/3 h-80 w-80 rounded-full bg-emerald-300/20 blur-3xl" />
      </div>

      <div className="relative mx-auto flex min-h-screen w-full max-w-7xl flex-col gap-6 px-4 py-6 sm:px-6 lg:px-8">
        <header className="overflow-hidden rounded-[32px] border border-white/50 bg-white/55 p-6 shadow-[0_24px_120px_rgba(124,58,237,.12)] backdrop-blur-xl">
          <div className="flex flex-col gap-6 lg:flex-row lg:items-end lg:justify-between">
            <div className="max-w-3xl">
              <p className="text-xs font-bold uppercase tracking-[0.45em] text-fuchsia-500">Super Marimo Voice</p>
              <h1 className="mt-3 text-3xl font-black tracking-tight text-slate-900 sm:text-5xl">
                프론트에서 바로 말하고, 듣고, 재생하는 마리모
              </h1>
              <p className="mt-3 max-w-2xl text-sm leading-7 text-slate-600">
                브라우저에서 음성 입력을 받고, 선택한 페르소나와 목소리로 답하게 만들었습니다.
                오른쪽에는 세션과 상태를 같이 보여줍니다.
              </p>
            </div>

            <div className="flex flex-wrap items-center gap-3">
              <span className={toneClass(overallOk, overallOk ? 'green' : 'rose')}>{overallOk ? 'LIVE' : 'DEGRADED'}</span>
              <span className="rounded-full border border-fuchsia-200 bg-white/70 px-3 py-1 text-xs text-slate-600">
                sync {syncedAt || 'waiting'}
              </span>
              <button
                type="button"
                onClick={() => void refreshOverview()}
                className="rounded-full border border-fuchsia-200 bg-fuchsia-500 px-4 py-2 text-xs font-semibold text-white transition hover:bg-fuchsia-600"
              >
                {isRefreshing ? 'refreshing' : 'refresh'}
              </button>
            </div>
          </div>

          <div className="mt-6 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
            {services.map((service) => (
              <StatTile
                key={service.label}
                title={service.label}
                value={service.ok ? 'Running' : 'Check required'}
                helper={service.detail}
                ok={service.ok}
              />
            ))}
          </div>
        </header>

        {globalError ? (
          <div className="rounded-[20px] border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
            {globalError}
          </div>
        ) : null}

        <main className="grid gap-6 xl:grid-cols-[1.05fr_0.95fr]">
          <section className="space-y-6">
            <div className="rounded-[32px] border border-white/50 bg-white/65 p-6 shadow-[0_20px_80px_rgba(236,72,153,.08)] backdrop-blur-xl">
              <div className="flex items-center justify-between gap-4">
                <div>
                  <h2 className="text-lg font-bold text-slate-900">대화 설정</h2>
                  <p className="mt-1 text-sm text-slate-500">페르소나와 목소리를 고르고 바로 대화합니다</p>
                </div>
                <div className="flex items-center gap-2">
                  <span className={toneClass(Boolean(voice?.ok && llm?.ok), voice?.ok && llm?.ok ? 'green' : 'amber')}>
                    {voice?.ok && llm?.ok ? 'READY' : 'WAIT'}
                  </span>
                  <button
                    type="button"
                    onClick={() => setAutoSpeak((value) => !value)}
                    className={[
                      'rounded-full border px-3 py-1.5 text-xs font-semibold transition',
                      autoSpeak
                        ? 'border-emerald-200 bg-emerald-500/15 text-emerald-700'
                        : 'border-slate-200 bg-slate-100 text-slate-600',
                    ].join(' ')}
                  >
                    {autoSpeak ? 'auto tts on' : 'auto tts off'}
                  </button>
                </div>
              </div>

              <div className="mt-6 grid gap-4">
                <label className="block">
                  <div className="mb-2 text-xs font-bold uppercase tracking-[0.3em] text-slate-500">persona preset</div>
                  <select
                    value={selectedPersonaId}
                    onChange={(event) => setSelectedPersonaId(event.target.value as (typeof PERSONA_PRESETS)[number]['id'])}
                    className="w-full rounded-[20px] border border-white/70 bg-white/80 px-4 py-3 text-sm text-slate-800 outline-none transition focus:border-fuchsia-300"
                  >
                    {PERSONA_PRESETS.map((preset) => (
                      <option key={preset.id} value={preset.id}>
                        {preset.label}
                      </option>
                    ))}
                  </select>
                </label>

                {selectedPersonaId === 'custom' ? (
                  <label className="block">
                    <div className="mb-2 text-xs font-bold uppercase tracking-[0.3em] text-slate-500">custom memo</div>
                    <textarea
                      value={customPersonaMemo}
                      onChange={(event) => setCustomPersonaMemo(event.target.value)}
                      rows={4}
                      className="w-full rounded-[20px] border border-white/70 bg-white/80 px-4 py-3 text-sm text-slate-800 outline-none transition focus:border-fuchsia-300"
                      placeholder="예: 한국인 꼬마 느낌으로, 다정하고 예의 바르게 말하기"
                    />
                  </label>
                ) : (
                  <div className="rounded-[20px] border border-fuchsia-100 bg-fuchsia-50 p-4 text-sm leading-7 text-slate-700">
                    <div className="mb-2 text-xs font-bold uppercase tracking-[0.3em] text-fuchsia-500">{selectedPersonaLabel}</div>
                    {selectedPersonaMemo}
                  </div>
                )}

                <label className="block">
                  <div className="mb-2 text-xs font-bold uppercase tracking-[0.3em] text-slate-500">voice model</div>
                  <select
                    value={selectedVoiceName}
                    onChange={(event) => setSelectedVoiceName(event.target.value)}
                    className="w-full rounded-[20px] border border-white/70 bg-white/80 px-4 py-3 text-sm text-slate-800 outline-none transition focus:border-fuchsia-300"
                    disabled={!voiceOptions.length}
                  >
                    {voiceOptions.length ? (
                      voiceOptions.map((name) => (
                        <option key={name} value={name}>
                          {name}
                        </option>
                      ))
                    ) : (
                      <option value="">loading...</option>
                    )}
                  </select>
                  <div className="mt-2 text-xs text-slate-500">
                    runtime: {voice?.tts_runtime_voice_name ?? voice?.tts_voice_name ?? 'none'}
                  </div>
                </label>

                <div className="grid gap-3 md:grid-cols-[1fr_auto_auto]">
                  <label className="block">
                    <div className="mb-2 text-xs font-bold uppercase tracking-[0.3em] text-slate-500">message</div>
                    <input
                      value={draftQuestion}
                      onChange={(event) => setDraftQuestion(event.target.value)}
                      onKeyDown={(event) => {
                        if (event.key === 'Enter') {
                          event.preventDefault();
                          void sendQuestion();
                        }
                      }}
                      className="w-full rounded-[20px] border border-white/70 bg-white/80 px-4 py-3 text-sm text-slate-800 outline-none transition focus:border-fuchsia-300"
                      placeholder="예: 지금 약간 피곤해"
                    />
                  </label>

                  <button
                    type="button"
                    onClick={() => void sendQuestion()}
                    disabled={isSending || !draftQuestion.trim()}
                    className="mt-7 rounded-[20px] bg-gradient-to-r from-fuchsia-500 to-cyan-500 px-5 py-3 text-sm font-bold text-white shadow-[0_12px_30px_rgba(236,72,153,.25)] transition hover:opacity-95 disabled:cursor-not-allowed disabled:opacity-50"
                  >
                    {isSending ? 'sending...' : 'send'}
                  </button>

                  <button
                    type="button"
                    onClick={startRecognition}
                    disabled={isSending}
                    className={[
                      'mt-7 rounded-[20px] px-5 py-3 text-sm font-bold text-white shadow-[0_12px_30px_rgba(14,165,233,.22)] transition disabled:cursor-not-allowed disabled:opacity-50',
                      isListening
                        ? 'bg-gradient-to-r from-rose-500 to-orange-500'
                        : 'bg-gradient-to-r from-sky-500 to-emerald-500',
                    ].join(' ')}
                  >
                    {isListening ? 'listening...' : 'mic'}
                  </button>
                </div>

                {askError ? (
                  <div className="rounded-[18px] border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
                    {askError}
                  </div>
                ) : null}

                {lastAskResult ? (
                  <div className="rounded-[22px] border border-cyan-100 bg-cyan-50 p-4">
                    <div className="flex items-center justify-between gap-3 text-xs font-bold uppercase tracking-[0.3em] text-cyan-600">
                      <span>latest ask</span>
                      <span>{lastAskResult.tts_ok ? 'tts ok' : 'tts skipped'}</span>
                    </div>
                    <div className="mt-3 space-y-2 text-sm text-slate-700">
                      <div>session: {lastAskResult.session_id}</div>
                      <div className="rounded-[18px] border border-cyan-100 bg-white p-3 text-slate-800">
                        {lastAskResult.answer}
                      </div>
                    </div>
                  </div>
                ) : null}
              </div>
            </div>

            <div className="rounded-[32px] border border-white/50 bg-white/65 p-6 shadow-[0_20px_80px_rgba(168,85,247,.08)] backdrop-blur-xl">
              <div className="flex items-center justify-between gap-4">
                <div>
                  <h2 className="text-lg font-bold text-slate-900">대화 기록</h2>
                  <p className="mt-1 text-sm text-slate-500">브라우저에서 바로 주고받는 메시지</p>
                </div>
                <span className="rounded-full border border-fuchsia-200 bg-fuchsia-50 px-3 py-1 text-xs font-semibold text-fuchsia-700">
                  {chatMessages.length} turns
                </span>
              </div>

              <div ref={chatScrollRef} className="mt-6 max-h-[520px] space-y-3 overflow-y-auto pr-1">
                {chatMessages.length ? (
                  chatMessages.map((message) => (
                    <MessageBubble
                      key={message.id}
                      role={message.role}
                      content={message.content}
                      createdAt={message.createdAt}
                    />
                  ))
                ) : (
                  <div className="rounded-[22px] border border-dashed border-fuchsia-200 bg-white/60 p-6 text-sm text-slate-500">
                    왼쪽에서 메시지를 보내면 여기 쌓입니다.
                  </div>
                )}
              </div>
            </div>

            <div className="rounded-[32px] border border-white/50 bg-white/65 p-6 shadow-[0_20px_80px_rgba(14,165,233,.08)] backdrop-blur-xl">
              <div className="flex items-center justify-between gap-4">
                <div>
                  <h2 className="text-lg font-bold text-slate-900">Sensor snapshot</h2>
                  <p className="mt-1 text-sm text-slate-500">latest realtime / hourly / merged data</p>
                </div>
                <span className={toneClass(Boolean(latestMerged), latestMerged?.state_level ? levelTone(latestMerged.state_level) : 'green')}>
                  {latestMerged ? latestMerged.state_level ?? 'normal' : 'no data'}
                </span>
              </div>

              <div className="mt-6 grid gap-3 md:grid-cols-3">
                <SensorMetric label="temperature" value={latestMerged?.temperature ?? latestHourly?.temperature} suffix=" C" />
                <SensorMetric label="humidity" value={latestMerged?.humidity ?? latestHourly?.humidity} suffix="%" />
                <SensorMetric label="light" value={latestMerged?.light ?? latestRealtime?.light} />
                <SensorMetric label="water level" value={latestMerged?.water_level ?? latestHourly?.water_level} suffix="%" />
                <SensorMetric label="distance" value={latestMerged?.distance ?? latestRealtime?.distance} suffix="cm" />
                <SensorMetric label="reading time" value={formatDateTime(latestMerged?.created_at ?? latestRealtime?.created_at ?? latestHourly?.created_at)} />
              </div>
            </div>
          </section>

          <section className="space-y-6">
            <div className="rounded-[32px] border border-white/50 bg-white/65 p-6 shadow-[0_20px_80px_rgba(244,63,94,.07)] backdrop-blur-xl">
              <div className="flex items-center justify-between gap-4">
                <div>
                  <h2 className="text-lg font-bold text-slate-900">Service health</h2>
                  <p className="mt-1 text-sm text-slate-500">API, STT/TTS, LLM status</p>
                </div>
                <span className={toneClass(overallOk, overallOk ? 'green' : 'rose')}>{overallOk ? 'ALL GREEN' : 'CHECK'}</span>
              </div>

              <div className="mt-6 grid gap-3">
                {[
                  {
                    name: 'voice-agent',
                    detail: agent ? `api-server ${agent.api_server.ok ? 'connected' : 'check'}` : 'loading',
                    ok: Boolean(agent?.ok),
                    lines: [`default STT: ${agent?.default_stt_model ?? 'none'}`, `session: ${agent?.session_id ?? 'none'}`],
                  },
                  {
                    name: 'api-server',
                    detail: 'DB / events / sessions',
                    ok: Boolean(api?.ok),
                    lines: [`DB: ${api?.db?.ok ? 'connected' : 'check required'}`, api?.llm_server_url ?? 'none'],
                  },
                  {
                    name: 'voice-server',
                    detail: voice?.tts_backend ?? 'loading',
                    ok: Boolean(voice?.ok),
                    lines: [
                      `TTS ready: ${voice?.tts_ready ? 'yes' : 'no'}`,
                      `voice: ${voice?.tts_runtime_voice_name ?? voice?.tts_voice_name ?? 'none'}`,
                    ],
                  },
                  {
                    name: 'llm-server',
                    detail: llm?.model ?? 'loading',
                    ok: Boolean(llm?.ok),
                    lines: [`mode: ${llm?.mode ?? 'none'}`, `device: ${llm?.device ?? 'none'}`],
                  },
                ].map((item) => (
                  <div key={item.name} className="rounded-[24px] border border-white/15 bg-white/85 p-4 shadow-[0_12px_30px_rgba(0,0,0,.04)]">
                    <div className="flex items-center justify-between gap-3">
                      <div>
                        <div className="text-sm font-semibold text-slate-900">{item.name}</div>
                        <div className="mt-1 text-xs text-slate-500">{item.detail}</div>
                      </div>
                      <span className={toneClass(item.ok, statusTone(item.ok))}>{item.ok ? 'OK' : 'WAIT'}</span>
                    </div>
                    <div className="mt-3 space-y-1 text-sm text-slate-600">
                      {item.lines.map((line) => (
                        <div key={line}>{line}</div>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            </div>

            <div className="rounded-[32px] border border-white/50 bg-white/65 p-6 shadow-[0_20px_80px_rgba(168,85,247,.07)] backdrop-blur-xl">
              <div className="flex items-center justify-between gap-4">
                <div>
                  <h2 className="text-lg font-bold text-slate-900">Command sessions</h2>
                  <p className="mt-1 text-sm text-slate-500">recent voice-console sessions</p>
                </div>
                <span className="rounded-full border border-fuchsia-200 bg-fuchsia-50 px-3 py-1 text-xs font-semibold text-fuchsia-700">
                  {sessions.length} items
                </span>
              </div>

              <div className="mt-6 space-y-3">
                {sessions.length ? (
                  sessions.map((session) => (
                    <SessionRow
                      key={session.session_id}
                      session={session}
                      active={session.session_id === selectedSessionId}
                      onSelect={() => setSelectedSessionId(session.session_id)}
                    />
                  ))
                ) : (
                  <div className="rounded-[22px] border border-dashed border-fuchsia-200 bg-white/70 p-6 text-sm text-slate-500">
                    No sessions yet.
                  </div>
                )}
              </div>
            </div>

            <div className="rounded-[32px] border border-white/50 bg-white/65 p-6 shadow-[0_20px_80px_rgba(34,197,94,.08)] backdrop-blur-xl">
              <div className="flex items-center justify-between gap-4">
                <div>
                  <h2 className="text-lg font-bold text-slate-900">Selected session</h2>
                  <p className="mt-1 text-sm text-slate-500">session detail and timeline</p>
                </div>
                <span className="rounded-full border border-emerald-200 bg-emerald-50 px-3 py-1 text-xs font-semibold text-emerald-700">
                  {selectedSessionIndex >= 0 ? `${selectedSessionIndex + 1} / ${sessions.length}` : '0 / 0'}
                </span>
              </div>

              {sessionError ? (
                <div className="mt-4 rounded-[18px] border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
                  {sessionError}
                </div>
              ) : null}

              {selectedSession ? (
                <div className="mt-6 space-y-6">
                  <div className="grid gap-3 md:grid-cols-4">
                    <SensorMetric label="turn count" value={selectedSession.session.turn_count} />
                    <SensorMetric label="messages" value={selectedSession.messages.length} />
                    <SensorMetric label="created" value={formatDateTime(selectedSession.session.created_at)} />
                    <SensorMetric label="ended" value={formatDateTime(selectedSession.session.ended_at)} />
                  </div>

                  <div className="rounded-[22px] border border-white/15 bg-white/75 p-4">
                    <div className="text-[11px] font-bold uppercase tracking-[0.3em] text-slate-500">meta</div>
                    <pre className="mt-3 overflow-auto text-xs leading-6 text-slate-700">
                      {JSON.stringify(selectedSession.session.meta, null, 2)}
                    </pre>
                  </div>

                  <div className="space-y-3">
                    {selectedSession.messages.length ? (
                      selectedSession.messages.map((message) => (
                        <MessageBubble
                          key={message.message_id}
                          role={message.role}
                          content={message.content}
                          createdAt={message.created_at}
                        />
                      ))
                    ) : (
                      <div className="rounded-[22px] border border-dashed border-white/30 bg-white/70 p-4 text-sm text-slate-500">
                        No messages.
                      </div>
                    )}
                  </div>
                </div>
              ) : (
                <div className="mt-6 rounded-[22px] border border-dashed border-white/30 bg-white/70 p-6 text-sm text-slate-500">
                  No session selected.
                </div>
              )}
            </div>
          </section>
        </main>
      </div>
    </div>
  );
}

export default App;
