import { useEffect, useMemo, useState } from 'react';
import { askAgent, checkAgentHealth, type AgentHealth, type AskResult } from './api';

const quickPrompts = [
  '오늘 상태를 한 번 요약해줘',
  'voice-agent 연결 상태 알려줘',
  'llm-server가 살아있는지 확인해줘',
  '테스트용 응답 문장 하나만 만들어줘',
];

const signalIcons = [
  '/images/incoming/icon-sound.png',
  '/images/incoming/icon-notification.png',
  '/images/incoming/icon-light.png',
  '/images/incoming/icon-theme.png',
];

function statusClass(ok: boolean) {
  return ok
    ? 'inline-flex items-center rounded-full bg-emerald-400/15 px-3 py-1 text-xs font-semibold text-emerald-200 ring-1 ring-emerald-300/30'
    : 'inline-flex items-center rounded-full bg-rose-400/15 px-3 py-1 text-xs font-semibold text-rose-200 ring-1 ring-rose-300/30';
}

function statusDot(ok: boolean) {
  return ok ? 'bg-emerald-400 shadow-[0_0_16px_rgba(52,211,153,0.6)]' : 'bg-rose-400 shadow-[0_0_16px_rgba(248,113,113,0.6)]';
}

export default function App() {
  const [health, setHealth] = useState<AgentHealth | null>(null);
  const [text, setText] = useState('오늘 상태를 한 번 요약해줘');
  const [sessionId, setSessionId] = useState('');
  const [result, setResult] = useState<AskResult | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [tick, setTick] = useState('');

  useEffect(() => {
    const updateClock = () => {
      setTick(
        new Date().toLocaleTimeString('ko-KR', {
          hour: '2-digit',
          minute: '2-digit',
          second: '2-digit',
          hour12: false,
        }),
      );
    };

    updateClock();
    const timer = window.setInterval(updateClock, 1000);
    return () => window.clearInterval(timer);
  }, []);

  useEffect(() => {
    const poll = async () => {
      try {
        const data = await checkAgentHealth();
        setHealth(data);
        setSessionId(data.session_id ?? '');
      } catch (err) {
        setError(err instanceof Error ? err.message : 'health check failed');
      }
    };

    void poll();
    const timer = window.setInterval(poll, 5000);
    return () => window.clearInterval(timer);
  }, []);

  const overallOk = useMemo(() => {
    return Boolean(health?.ok && health.voice_server.ok && health.llm_server.ok);
  }, [health]);

  const healthRows = [
    { label: 'voice-agent', ok: Boolean(health?.ok), value: health?.ok ? 'online' : 'waiting' },
    { label: 'voice-server', ok: Boolean(health?.voice_server.ok), value: health?.voice_server.ok ? 'online' : 'waiting' },
    { label: 'llm-server', ok: Boolean(health?.llm_server.ok), value: health?.llm_server.ok ? 'online' : 'waiting' },
  ];

  const runAsk = async () => {
    setBusy(true);
    setError('');

    try {
      const data = await askAgent(text, sessionId || undefined);
      setResult(data);
      setSessionId(data.session_id);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'ask failed');
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="app-shell min-h-screen text-slate-100">
      <div className="app-shell__overlay" aria-hidden="true" />
      <main className="page-shell mx-auto flex min-h-screen w-full max-w-7xl flex-col gap-6 px-4 py-5 sm:px-6 lg:px-8">
        <header className="panel-surface hero-panel overflow-hidden">
          <div className="grid gap-8 lg:grid-cols-[1.05fr_0.95fr] lg:items-center">
            <div className="relative z-10 space-y-6 p-6 sm:p-8">
              <div className="inline-flex items-center gap-2 rounded-full bg-white/10 px-3 py-1 text-xs font-semibold uppercase tracking-[0.3em] text-cyan-100 ring-1 ring-white/10">
                <span className={`h-2.5 w-2.5 rounded-full ${statusDot(overallOk)}`} />
                Super_Marimo live console
              </div>

              <div className="space-y-4">
                <p className="max-w-2xl text-sm leading-6 text-slate-200/90 sm:text-base">
                  음성 에이전트와 서버 상태를 한눈에 확인하고, 바로 질문을 던질 수 있는 대시보드입니다.
                  기존 구조는 유지하면서 이미지와 분위기만 더 풍성하게 다듬었습니다.
                </p>
                <div className="space-y-3">
                  <h1 className="text-4xl font-bold tracking-tight text-white sm:text-5xl">
                    Marimo가 있는
                    <br />
                    따뜻한 상태 대시보드
                  </h1>
                  <p className="max-w-xl text-sm leading-6 text-slate-300 sm:text-base">
                    서버 상태, 세션 정보, 응답 결과를 정리된 카드로 보여주고,
                    오른쪽의 캐릭터 씬에서 프로젝트 분위기를 시각적으로 살렸습니다.
                  </p>
                </div>
              </div>

              <div className="flex flex-wrap gap-3">
                <div className="metric-pill">
                  <span className="metric-pill__label">state</span>
                  <span className="metric-pill__value">{overallOk ? 'all systems go' : 'checking'}</span>
                </div>
                <div className="metric-pill">
                  <span className="metric-pill__label">session</span>
                  <span className="metric-pill__value">{sessionId || '-'}</span>
                </div>
                <div className="metric-pill">
                  <span className="metric-pill__label">clock</span>
                  <span className="metric-pill__value">{tick || '--:--:--'}</span>
                </div>
              </div>

              <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
                {[
                  ['음성', health?.voice_server.ok ?? false, '/images/incoming/icon-sound.png'],
                  ['세션', Boolean(sessionId), '/images/incoming/icon-notification.png'],
                  ['조명', overallOk, '/images/incoming/icon-light.png'],
                  ['테마', true, '/images/incoming/icon-theme.png'],
                ].map(([label, ok, icon], index) => (
                  <div key={label as string} className="mini-stat">
                    <img src={signalIcons[index] ?? (icon as string)} alt="" className="mini-stat__icon" />
                    <div className="min-w-0">
                      <div className="text-xs uppercase tracking-[0.24em] text-slate-400">{label}</div>
                      <div className="mt-1 flex items-center gap-2">
                        <span className={`h-2.5 w-2.5 rounded-full ${statusDot(Boolean(ok))}`} />
                        <span className="text-sm font-semibold text-white">{Boolean(ok) ? 'ready' : 'standby'}</span>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            <div className="relative px-4 pb-8 pt-0 sm:px-6 lg:px-4 lg:py-8">
              <div className="scene-wrap">
                <img
                  src="/images/incoming/home-background.png"
                  alt=""
                  className="scene-wrap__bg"
                  aria-hidden="true"
                />
                <div className="scene-wrap__veil" aria-hidden="true" />

                <div className="scene-board">
                  <img
                    src="/images/incoming/information-board2.png"
                    alt=""
                    className="scene-board__frame"
                    aria-hidden="true"
                  />
                  <div className="scene-board__content">
                    <div className="flex items-center justify-between gap-3">
                      <div>
                        <p className="text-[0.62rem] uppercase tracking-[0.35em] text-amber-100/70">status board</p>
                        <h2 className="mt-2 text-2xl font-bold text-white">현재 연결 상태</h2>
                      </div>
                      <div className={statusClass(overallOk)}>{overallOk ? 'ALL OK' : 'DEGRADED'}</div>
                    </div>

                    <div className="mt-5 space-y-3">
                      {healthRows.map((row) => (
                        <div key={row.label} className="status-row">
                          <div>
                            <div className="text-sm font-semibold text-white">{row.label}</div>
                            <div className="text-xs text-slate-200/70">{row.value}</div>
                          </div>
                          <span className={statusClass(row.ok)}>{row.ok ? 'OK' : 'WAIT'}</span>
                        </div>
                      ))}
                    </div>

                    <div className="mt-5 rounded-3xl bg-black/20 p-4 ring-1 ring-white/10">
                      <div className="text-xs uppercase tracking-[0.32em] text-slate-300/70">hint</div>
                      <p className="mt-2 text-sm leading-6 text-slate-100">
                        아래 입력창에서 질문을 보내면 음성 에이전트가 답을 가져옵니다.
                        세션이 있으면 이어서 대화를 계속합니다.
                      </p>
                    </div>
                  </div>
                </div>

                <img
                  src="/images/incoming/marimo-main.png"
                  alt="Marimo character"
                  className="scene-wrap__marimo"
                />
              </div>
            </div>
          </div>
        </header>

        <section className="grid gap-6 lg:grid-cols-[1.15fr_0.85fr]">
          <div className="panel-surface p-6 sm:p-7">
            <div className="flex items-start justify-between gap-4">
              <div>
                <p className="text-xs uppercase tracking-[0.35em] text-cyan-200/80">ask marimo</p>
                <h2 className="mt-2 text-2xl font-bold text-white">Agent Ask</h2>
                <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-300">
                  문장을 입력하면 `voice-agent`로 전달하고, `voice-server`와 `llm-server` 연결 상태도 함께 확인합니다.
                </p>
              </div>
              <div className="hidden rounded-2xl bg-white/5 px-4 py-3 text-right ring-1 ring-white/10 sm:block">
                <div className="text-xs uppercase tracking-[0.28em] text-slate-400">session</div>
                <div className="mt-1 text-sm font-semibold text-white">{sessionId || 'new'}</div>
              </div>
            </div>

            <div className="mt-6 flex flex-wrap gap-2">
              {quickPrompts.map((prompt) => (
                <button
                  key={prompt}
                  type="button"
                  className="prompt-chip"
                  onClick={() => setText(prompt)}
                >
                  {prompt}
                </button>
              ))}
            </div>

            <label className="mt-6 block text-sm font-medium text-slate-200">질문</label>
            <textarea
              className="mt-2 min-h-36 w-full resize-none rounded-3xl border border-white/10 bg-slate-950/60 p-4 text-base leading-7 text-white outline-none transition placeholder:text-slate-500 focus:border-cyan-300/60 focus:ring-2 focus:ring-cyan-300/20"
              value={text}
              onChange={(e) => setText(e.target.value)}
              placeholder="Marimo에게 물어보고 싶은 내용을 적어보세요."
            />

            <div className="mt-4 flex flex-wrap gap-3">
              <button
                className="primary-action"
                onClick={() => void runAsk()}
                disabled={busy || !text.trim()}
              >
                {busy ? '보내는 중...' : 'voice-agent에게 보내기'}
              </button>
              <button
                className="secondary-action"
                onClick={() => setText('오늘 상태를 한 번 요약해줘')}
                type="button"
              >
                기본 문장
              </button>
            </div>

            {error ? (
              <div className="mt-4 rounded-3xl border border-rose-400/30 bg-rose-500/10 p-4 text-sm leading-6 text-rose-100">
                {error}
              </div>
            ) : null}

            <div className="mt-6 rounded-3xl border border-white/10 bg-black/20 p-5">
              <div className="text-xs uppercase tracking-[0.32em] text-slate-400">response</div>
              <div className="mt-3 text-lg leading-8 text-white">
                {result?.answer || '아직 응답이 없습니다. 질문을 보내면 답변이 여기에 표시됩니다.'}
              </div>
              <div className="mt-5 grid gap-3 text-sm text-slate-300 sm:grid-cols-2">
                <div className="rounded-2xl bg-white/5 p-3 ring-1 ring-white/10">tts: {result ? String(result.tts_ok) : '-'}</div>
                <div className="rounded-2xl bg-white/5 p-3 ring-1 ring-white/10">session: {result?.session_id || sessionId || '-'}</div>
                <div className="rounded-2xl bg-white/5 p-3 ring-1 ring-white/10">voice ok: {result ? String(result.voice_health.ok) : '-'}</div>
                <div className="rounded-2xl bg-white/5 p-3 ring-1 ring-white/10">llm ok: {result ? String(result.llm_health.ok) : '-'}</div>
              </div>
            </div>
          </div>

          <div className="space-y-6">
            <div className="panel-surface p-6 sm:p-7">
              <div className="flex items-center justify-between gap-3">
                <div>
                  <p className="text-xs uppercase tracking-[0.35em] text-cyan-200/80">health</p>
                  <h2 className="mt-2 text-2xl font-bold text-white">서비스 상태</h2>
                </div>
                <div className={statusClass(overallOk)}>{overallOk ? 'STABLE' : 'CHECKING'}</div>
              </div>

              <div className="mt-5 space-y-3">
                {healthRows.map((row) => (
                  <div key={row.label} className="status-row">
                    <div className="flex items-center gap-3">
                      <span className={`h-3 w-3 rounded-full ${statusDot(row.ok)}`} />
                      <div>
                        <div className="text-sm font-semibold text-white">{row.label}</div>
                        <div className="text-xs text-slate-300">{row.value}</div>
                      </div>
                    </div>
                    <span className={statusClass(row.ok)}>{row.ok ? 'OK' : 'WAIT'}</span>
                  </div>
                ))}

                <div className="status-row">
                  <div>
                    <div className="text-sm font-semibold text-white">default stt</div>
                    <div className="text-xs text-slate-300">{health?.default_stt_model ?? '-'}</div>
                  </div>
                  <span className="rounded-full bg-white/5 px-3 py-1 text-xs font-semibold text-slate-200 ring-1 ring-white/10">
                    model
                  </span>
                </div>
              </div>
            </div>

            <div className="panel-surface p-6 sm:p-7">
              <div className="flex items-center justify-between gap-3">
                <div>
                  <p className="text-xs uppercase tracking-[0.35em] text-cyan-200/80">debug</p>
                  <h2 className="mt-2 text-2xl font-bold text-white">Raw Data</h2>
                </div>
                <div className="rounded-full bg-white/5 px-3 py-1 text-xs font-semibold text-slate-200 ring-1 ring-white/10">
                  live json
                </div>
              </div>

              <pre className="mt-5 overflow-auto rounded-3xl bg-slate-950/80 p-4 text-xs leading-6 text-slate-300 ring-1 ring-white/10">
                {JSON.stringify({ health, result }, null, 2)}
              </pre>
            </div>
          </div>
        </section>
      </main>
    </div>
  );
}
