import { useEffect, useRef, useState } from 'react';
import { askChat, getSessionDetail, listSessions, synthesizeTts, type SessionDetail, type SessionSummary } from '../api';

declare global {
  interface Window {
    SpeechRecognition?: new () => SpeechRecognition;
    webkitSpeechRecognition?: new () => SpeechRecognition;
  }
}

interface SpeechRecognition extends EventTarget {
  lang: string;
  interimResults: boolean;
  continuous: boolean;
  start: () => void;
  stop: () => void;
  onresult: ((event: SpeechRecognitionEvent) => void) | null;
  onend: (() => void) | null;
  onerror: ((event: { error?: string }) => void) | null;
}

interface SpeechRecognitionEvent {
  results: ArrayLike<{ 0: { transcript: string } }>;
}

export function ChatPage() {
  const [sessions, setSessions] = useState<SessionSummary[]>([]);
  const [detail, setDetail] = useState<SessionDetail | null>(null);
  const [sessionId, setSessionId] = useState<string | undefined>(undefined);
  const [input, setInput] = useState('');
  const [busy, setBusy] = useState(false);
  const [recording, setRecording] = useState(false);
  const [error, setError] = useState('');
  const feedRef = useRef<HTMLDivElement>(null);
  const recognitionRef = useRef<SpeechRecognition | null>(null);

  const refreshSessions = async (selectId?: string) => {
    const rows = await listSessions(30);
    setSessions(rows);
    const nextId = selectId ?? sessionId ?? rows[0]?.session_id;
    if (nextId) {
      setSessionId(nextId);
      setDetail(await getSessionDetail(nextId));
    }
  };

  useEffect(() => {
    void refreshSessions();
  }, []);

  useEffect(() => {
    feedRef.current?.scrollTo(0, feedRef.current.scrollHeight);
  }, [detail]);

  const selectSession = async (id: string) => {
    setError('');
    setSessionId(id);
    setDetail(await getSessionDetail(id));
  };

  const newSession = () => {
    setSessionId(undefined);
    setDetail(null);
    setInput('');
  };

  const send = async (text = input) => {
    const value = text.trim();
    if (!value || busy) return;
    setBusy(true);
    setError('');
    try {
      const result = await askChat(value, sessionId);
      const nextId = result.session_id;
      setInput('');
      await refreshSessions(nextId);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'send failed');
    } finally {
      setBusy(false);
    }
  };

  const startVoiceInput = () => {
    const SpeechCtor = window.SpeechRecognition ?? window.webkitSpeechRecognition;
    if (!SpeechCtor) {
      setError('이 브라우저는 SpeechRecognition을 지원하지 않습니다.');
      return;
    }
    setError('');
    const recognition = new SpeechCtor();
    recognition.lang = 'ko-KR';
    recognition.interimResults = false;
    recognition.continuous = false;
    recognition.onresult = (event) => {
      const transcript = String(event.results[0]?.[0]?.transcript ?? '').trim();
      if (transcript) {
        setInput(transcript);
        void send(transcript);
      }
    };
    recognition.onerror = (event) => setError(event.error || 'voice input failed');
    recognition.onend = () => setRecording(false);
    recognitionRef.current = recognition;
    setRecording(true);
    recognition.start();
  };

  const stopVoiceInput = () => {
    recognitionRef.current?.stop();
    setRecording(false);
  };

  const play = async (text: string) => {
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
    <div className="grid min-h-[calc(100vh-140px)] gap-4 lg:grid-cols-[300px_1fr]">
      <aside className="pixel-card flex min-h-0 flex-col">
        <div className="mb-3 flex items-center justify-between gap-2">
          <h1 className="font-pixel text-lg text-grass">Chat</h1>
          <button onClick={newSession} className="rounded-lg border-2 border-grass bg-grass/10 px-3 py-1 font-dot text-xs text-grass">
            new
          </button>
        </div>
        <div className="flex min-h-0 flex-col gap-2 overflow-y-auto">
          {sessions.map((session) => (
            <button
              key={session.session_id}
              type="button"
              onClick={() => void selectSession(session.session_id)}
              className={[
                'rounded-xl border-2 p-3 text-left transition',
                session.session_id === sessionId ? 'border-grass bg-grass/15' : 'border-bark/15 bg-white/60 hover:border-grass/50',
              ].join(' ')}
            >
              <div className="font-dot text-xs text-bark">{session.title || 'New chat'}</div>
              <div className="mt-1 truncate font-dot text-[10px] text-bark/50">{session.preview || session.session_id}</div>
            </button>
          ))}
          {sessions.length === 0 && <div className="font-dot text-xs text-bark/50">No sessions yet.</div>}
        </div>
      </aside>

      <section className="pixel-card flex min-h-0 flex-col">
        <div className="mb-3 flex flex-wrap items-center justify-between gap-2 border-b border-bark/10 pb-3">
          <div>
            <div className="font-pixel text-sm text-bark">{sessionId ? `session ${sessionId.slice(0, 8)}` : 'new session'}</div>
            <div className="font-dot text-[10px] text-bark/50">웹 채팅은 LLM 답변만 받고 자동 TTS를 만들지 않습니다.</div>
          </div>
          <button
            type="button"
            onClick={recording ? stopVoiceInput : startVoiceInput}
            className={[
              'rounded-xl border-2 px-4 py-2 font-dot text-xs transition',
              recording ? 'border-heart-red bg-heart-red/15 text-heart-red' : 'border-sky bg-sky/15 text-sky',
            ].join(' ')}
          >
            {recording ? '음성 중지' : '음성 입력'}
          </button>
        </div>

        {error && <div className="mb-3 rounded-lg border-2 border-heart-red bg-heart-red/10 p-2 font-dot text-xs text-heart-red">{error}</div>}

        <div ref={feedRef} className="flex-1 overflow-y-auto rounded-xl bg-white/40 p-3">
          <div className="flex flex-col gap-3">
            {(detail?.messages ?? []).map((message) => {
              const isUser = message.role === 'user';
              return (
                <div key={message.message_id} className={isUser ? 'self-end' : 'self-start'}>
                  <div className={isUser ? 'chat-bubble-player max-w-[720px]' : 'chat-bubble-npc max-w-[720px]'}>
                    <div className="whitespace-pre-wrap font-dot text-sm text-bark">{message.content}</div>
                    <div className="mt-2 flex items-center justify-between gap-2">
                      <span className="font-dot text-[10px] text-bark/45">
                        {message.meta?.source ? String(message.meta.source) : message.role} · {new Date(message.created_at).toLocaleString('ko-KR')}
                      </span>
                      {!isUser && (
                        <button onClick={() => void play(message.content)} className="tts-btn">
                          듣기
                        </button>
                      )}
                    </div>
                  </div>
                </div>
              );
            })}
            {!detail && <div className="py-12 text-center font-dot text-sm text-bark/45">새 대화를 시작하거나 왼쪽 세션을 선택하세요.</div>}
          </div>
        </div>

        <div className="mt-3 flex gap-2">
          <input
            className="pixel-input flex-1"
            value={input}
            onChange={(event) => setInput(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === 'Enter') void send();
            }}
            placeholder="메시지 입력..."
            disabled={busy}
          />
          <button
            onClick={() => void send()}
            disabled={busy}
            className="rounded-xl border-2 border-grass bg-grass/15 px-5 py-2 font-dot text-xs text-grass disabled:opacity-50"
          >
            {busy ? 'sending' : 'send'}
          </button>
        </div>
      </section>
    </div>
  );
}
