import { useEffect, useMemo, useState } from 'react';
import { askAgent, checkAgentHealth, type AgentHealth, type AskResult } from './api';
import { MarimoEntity } from './MarimoEntity';

function badge(ok: boolean) {
  return ok
    ? 'rounded-full bg-emerald-500 px-3 py-1 text-xs font-semibold text-white'
    : 'rounded-full bg-rose-500 px-3 py-1 text-xs font-semibold text-white';
}

export default function App() {
  const [health, setHealth] = useState<AgentHealth | null>(null);
  const [text, setText] = useState('안녕 마리모');
  const [sessionId, setSessionId] = useState('');
  const [result, setResult] = useState<AskResult | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [tick, setTick] = useState('');

  useEffect(() => {
    const updateClock = () => {
      setTick(new Date().toLocaleTimeString('ko-KR', { hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false }));
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
    <div className="min-h-screen bg-[#0f172a] text-slate-100">
      <div className="mx-auto flex min-h-screen w-full max-w-6xl flex-col gap-6 p-6">
        <header className="rounded-3xl border border-white/10 bg-slate-900/70 p-6 shadow-2xl backdrop-blur">
          <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
            <div>
              <p className="text-xs uppercase tracking-[0.35em] text-cyan-300">Super_Marimo</p>
              <h1 className="mt-2 text-3xl font-bold text-white">Voice Agent Beta Console</h1>
              <p className="mt-2 text-sm text-slate-300">
                로컬에서 voice-agent, voice-server, llm-server 상태를 확인하고 수동 질문을 던지는 베타 패널입니다.
              </p>
            </div>
            <div className={badge(overallOk)}>{overallOk ? 'ALL OK' : 'DEGRADED'}</div>
          </div>
          <div className="mt-4 flex flex-wrap gap-3 text-sm text-slate-300">
            <span className="rounded-full bg-white/5 px-3 py-1">agent: {health?.server ?? 'loading'}</span>
            <span className="rounded-full bg-white/5 px-3 py-1">session: {sessionId || '-'}</span>
            <span className="rounded-full bg-white/5 px-3 py-1">clock: {tick}</span>
          </div>
        </header>

        <section className="grid gap-6 lg:grid-cols-[1.2fr_0.8fr]">
          <div className="rounded-3xl border border-white/10 bg-slate-900/70 p-6 shadow-xl backdrop-blur">
            <h2 className="text-lg font-semibold text-white">Agent Ask</h2>
            <p className="mt-2 text-sm text-slate-400">
              입력한 문장을 <code>voice-agent</code>로 보내고, 내부에서 <code>voice-server</code> / <code>llm-server</code> 연결이 살아있는지 확인합니다.
            </p>

            <label className="mt-6 block text-sm text-slate-300">질문</label>
            <textarea
              className="mt-2 min-h-32 w-full rounded-2xl border border-white/10 bg-slate-950/70 p-4 text-base text-white outline-none ring-0 placeholder:text-slate-500"
              value={text}
              onChange={(e) => setText(e.target.value)}
              placeholder="예: 오늘 상태 어때?"
            />

            <div className="mt-4 flex flex-wrap gap-3">
              <button
                className="rounded-full bg-cyan-500 px-5 py-2.5 text-sm font-semibold text-slate-950 disabled:opacity-60"
                onClick={() => void runAsk()}
                disabled={busy || !text.trim()}
              >
                {busy ? '전송 중...' : 'voice-agent에 보내기'}
              </button>
              <button
                className="rounded-full border border-white/15 px-5 py-2.5 text-sm font-semibold text-white"
                onClick={() => setText('안녕 마리모')}
              >
                기본 문장
              </button>
            </div>

            {error ? (
              <div className="mt-4 rounded-2xl border border-rose-400/30 bg-rose-500/10 p-4 text-sm text-rose-200">
                {error}
              </div>
            ) : null}

            <div className="mt-6 rounded-3xl border border-white/10 bg-black/20 p-5">
              <div className="text-sm text-slate-400">응답</div>
              <div className="mt-2 text-lg leading-8 text-white">{result?.answer || '아직 응답이 없습니다.'}</div>
              <div className="mt-4 grid gap-2 text-xs text-slate-400 md:grid-cols-2">
                <div>tts: {result ? String(result.tts_ok) : '-'}</div>
                <div>session: {result?.session_id || sessionId || '-'}</div>
                <div>voice ok: {result ? String(result.voice_health.ok) : '-'}</div>
                <div>llm ok: {result ? String(result.llm_health.ok) : '-'}</div>
              </div>
            </div>
          </div>

          <div className="space-y-6">
            <div className="rounded-3xl border border-white/10 bg-slate-900/70 p-6 shadow-xl backdrop-blur">
              <h2 className="text-lg font-semibold text-white">Health</h2>
              <div className="mt-4 space-y-3 text-sm">
                <div className="flex items-center justify-between rounded-2xl bg-white/5 px-4 py-3">
                  <span>voice-agent</span>
                  <span className={badge(Boolean(health?.ok))}>{health?.ok ? 'OK' : 'WAIT'}</span>
                </div>
                <div className="flex items-center justify-between rounded-2xl bg-white/5 px-4 py-3">
                  <span>voice-server</span>
                  <span className={badge(Boolean(health?.voice_server.ok))}>{health?.voice_server.ok ? 'OK' : 'WAIT'}</span>
                </div>
                <div className="flex items-center justify-between rounded-2xl bg-white/5 px-4 py-3">
                  <span>llm-server</span>
                  <span className={badge(Boolean(health?.llm_server.ok))}>{health?.llm_server.ok ? 'OK' : 'WAIT'}</span>
                </div>
                <div className="flex items-center justify-between rounded-2xl bg-white/5 px-4 py-3">
                  <span>stt default</span>
                  <span className="text-slate-300">{health?.default_stt_model ?? '-'}</span>
                </div>
              </div>
            </div>

            <div className="rounded-3xl border border-white/10 bg-slate-900/70 p-6 shadow-xl backdrop-blur">
              <h2 className="text-lg font-semibold text-white">Raw</h2>
              <pre className="mt-4 overflow-auto rounded-2xl bg-black/30 p-4 text-xs text-slate-300">
                {JSON.stringify({ health, result }, null, 2)}
              </pre>
            </div>
          </div>
        </section>

        <div className="pb-8 text-center text-xs text-slate-500">
          <MarimoEntity size={180} className="mx-auto" />
        </div>
      </div>
    </div>
  );
}
