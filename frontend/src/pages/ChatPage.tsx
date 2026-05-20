import { useEffect, useRef, useState, type MouseEvent } from 'react';
import {
  askChat,
  deleteSession,
  getSessionDetail,
  listSessions,
  synthesizeTts,
  updateRuntimeSettings,
  type SessionDetail,
  type SessionSummary,
} from '../api';
import { flushSync } from 'react-dom';
import '../styles/report.css';
import '../styles/chat.css';
import '../styles/speech.css';

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

export function sanitizeMessageContent(content: string): string {
  if (!content) return '';

  const trimmed = content.trim();
  let target = trimmed;

  if (target.includes('```')) {
    target = target.replace(/```(?:json)?/gi, '').trim();
  }

  target = target.replace(/\s*\*+\s*$/, '').trim();

  const jsonStart = target.indexOf('{');
  const jsonEnd = target.lastIndexOf('}');
  if (jsonStart !== -1) {
    let jsonContent = target;
    if (jsonEnd > jsonStart) {
      jsonContent = target.slice(jsonStart, jsonEnd + 1);
    } else {
      jsonContent = target.slice(jsonStart);
    }

    try {
      const parsed = JSON.parse(jsonContent);
      if (parsed && typeof parsed === 'object') {
        const candidateKeys = ['answer', 'answe', 'answ', 'llm_answer', 'response', 'text'];
        for (const key of candidateKeys) {
          if (key in parsed) {
            return String((parsed as Record<string, unknown>)[key]);
          }
        }
      }
    } catch {
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

function formatClock(value: string) {
  try {
    return new Date(value).toLocaleTimeString('ko-KR', { hour: '2-digit', minute: '2-digit' });
  } catch {
    return '';
  }
}

function PlayIcon() {
  return (
    <svg aria-hidden="true" viewBox="0 0 24 24" fill="currentColor" className="h-4 w-4">
      <path d="M8 5.5v13l11-6.5-11-6.5Z" />
    </svg>
  );
}

function CopyIcon() {
  return (
    <svg aria-hidden="true" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.9" className="h-4 w-4">
      <rect x="9" y="9" width="10" height="10" rx="2" />
      <path d="M5 15V7a2 2 0 0 1 2-2h8" />
    </svg>
  );
}

function MicIcon() {
  return (
    <svg aria-hidden="true" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.9" className="h-4 w-4">
      <rect x="9" y="3" width="6" height="11" rx="3" />
      <path d="M5 11a7 7 0 0 0 14 0" />
      <path d="M12 18v3" />
      <path d="M8 21h8" />
    </svg>
  );
}

function TrashIcon() {
  return (
    <svg aria-hidden="true" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.9" className="h-4 w-4">
      <path d="M4 7h16" />
      <path d="M9 7V5.8A1.8 1.8 0 0 1 10.8 4h2.4A1.8 1.8 0 0 1 15 5.8V7" />
      <path d="M7 7l1 13h8l1-13" />
      <path d="M10 11v5M14 11v5" />
    </svg>
  );
}

function SidebarToggleIcon({ open }: { open: boolean }) {
  return (
    <svg aria-hidden="true" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.9" className="h-5 w-5">
      {open ? (
        <>
          <path d="M16 6l-6 6 6 6" />
        </>
      ) : (
        <>
          <path d="M5 7h14" />
          <path d="M5 12h14" />
          <path d="M5 17h14" />
        </>
      )}
    </svg>
  );
}

export function ChatPage() {
  const [sessions, setSessions] = useState<SessionSummary[]>([]);
  const [detail, setDetail] = useState<SessionDetail | null>(null);
  const [sessionId, setSessionId] = useState<string | undefined>(undefined);
  const [input, setInput] = useState('');
  const [busy, setBusy] = useState(false);
  const [recording, setRecording] = useState(false);
  const [error, setError] = useState('');
  const [actionNote, setActionNote] = useState('');
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const feedRef = useRef<HTMLDivElement>(null);
  const recognitionRef = useRef<SpeechRecognition | null>(null);

  const orderedMessages = [...(detail?.messages ?? [])].sort(
    (left, right) => Number(left.message_id) - Number(right.message_id),
  );
  const activeSession = sessions.find((session) => session.session_id === sessionId);
  const sidebarTitle = '대화 목록';
  const detailTitle = String(detail?.session?.meta?.title ?? '').trim();
  const sessionTitle = activeSession?.title?.trim() || detailTitle || '마리모 대화';

  const refreshSessions = async (selectId?: string) => {
    const rows = await listSessions(30);
    setSessions(rows);

    const nextId = selectId ?? sessionId ?? rows[0]?.session_id;
    if (nextId) {
      setSessionId(nextId);
      setDetail(await getSessionDetail(nextId));
      return;
    }

    setSessionId(undefined);
    setDetail(null);
  };

  useEffect(() => {
    void refreshSessions();
  }, []);

  useEffect(() => {
    feedRef.current?.scrollTo({
      top: feedRef.current.scrollHeight,
      behavior: 'smooth',
    });
  }, [detail, busy]);

  const handleDeleteSession = async (id: string, event: MouseEvent) => {
    event.stopPropagation();

    if (!window.confirm('선택한 대화를 정말 삭제하시겠습니까?')) return;

    try {
      await deleteSession(id);

      if (sessionId === id) {
        setSessionId(undefined);
        setDetail(null);
        setActionNote('');
        setError('');
        await refreshSessions();
        return;
      }

      await refreshSessions(sessionId);
    } catch (err) {
      setError(err instanceof Error ? err.message : '대화 삭제에 실패했습니다.');
    }
  };

  const selectSession = async (id: string) => {
    setError('');
    setSessionId(id);
    setDetail(await getSessionDetail(id));
  };

  const newSession = async () => {
    setSessionId(undefined);
    setDetail(null);
    setInput('');
    setActionNote('');
    setError('');

    try {
      await updateRuntimeSettings({ distance_inside_threshold: false });
    } catch {
      // background fail ignore
    }
  };

  const play = async (text: string) => {
    try {
      const blob = await synthesizeTts(text);
      const url = URL.createObjectURL(blob);
      const audio = new Audio(url);
      audio.onended = () => URL.revokeObjectURL(url);
      await audio.play();
    } catch (err) {
      setError(err instanceof Error ? err.message : '음성 재생에 실패했습니다.');
    }
  };

  const copyText = async (text: string) => {
    try {
      if (navigator.clipboard?.writeText && window.isSecureContext) {
        await navigator.clipboard.writeText(text);
        return;
      }

      const textarea = document.createElement('textarea');
      textarea.value = text;
      textarea.readOnly = true;
      textarea.style.position = 'fixed';
      textarea.style.top = '-9999px';
      textarea.style.left = '-9999px';
      textarea.style.opacity = '0';
      document.body.appendChild(textarea);
      textarea.focus();
      textarea.select();

      const copied = document.execCommand('copy');
      document.body.removeChild(textarea);

      if (!copied) {
        throw new Error('copy command failed');
      }
    } catch {
      setError('복사에 실패했습니다.');
    }
  };

  const appendOptimisticUserMessage = (text: string) => {
    const now = new Date().toISOString();
    const tempSessionId = sessionId ?? detail?.session?.session_id ?? `pending-${Date.now()}`;

    setDetail((current) => {
      const baseDetail =
        current ??
        ({
          session: {
            session_id: tempSessionId,
            created_at: now,
            last_seen_at: now,
            ended_at: null,
            turn_count: 0,
            meta: {},
          },
          messages: [],
        } satisfies SessionDetail);

      return {
        ...baseDetail,
        messages: [
          ...baseDetail.messages,
          {
            message_id: Date.now() * 1000,
            session_id: tempSessionId,
            role: 'user',
            content: text,
            created_at: now,
            meta: {},
          },
        ],
      };
    });
  };

  const send = async (text = input) => {
    const value = text.trim();
    if (!value || busy) return;

    const previousDetail = detail;
    const previousInput = input;
    flushSync(() => {
      setError('');
      setActionNote('');
      setInput('');
      appendOptimisticUserMessage(value);
      setBusy(true);
    });

    await new Promise<void>((resolve) => {
      window.requestAnimationFrame(() => resolve());
    });

    try {
      const result = await askChat(value, sessionId);
      const nextId = result.session_id;

      const action = result.action_result;
      if (action?.summary) {
        let note = action.summary;
        if (action.patch && 'web_voice_enabled' in action.patch) {
          note = `웹 음성 ${action.patch.web_voice_enabled ? '켜짐' : '꺼짐'} / ${note}`;
        }
        setActionNote(note);
      }

      await refreshSessions(nextId);
    } catch (err) {
      setDetail(previousDetail);
      setInput(previousInput);
      setError(err instanceof Error ? err.message : '전송에 실패했습니다.');
    } finally {
      setBusy(false);
    }
  };

  const startVoiceInput = () => {
    const SpeechCtor = window.SpeechRecognition ?? window.webkitSpeechRecognition;
    if (!SpeechCtor) {
      setError('이 브라우저는 음성 인식을 지원하지 않습니다.');
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
    recognition.onerror = (event) => setError(event.error || '음성 인식 실패');
    recognition.onend = () => setRecording(false);
    recognitionRef.current = recognition;
    setRecording(true);
    recognition.start();
  };

  const stopVoiceInput = () => {
    recognitionRef.current?.stop();
    setRecording(false);
  };

  return (
    <div
      className={`report-page sensor-stack report-screen chat-page font-dot grid h-full min-h-0 gap-4 overflow-hidden transition-all duration-300 ${
        sidebarOpen ? 'lg:grid-cols-[300px_1fr]' : 'lg:grid-cols-[0px_1fr]'
      }`}
    >
      <div className={`chat-sidebar-backdrop ${sidebarOpen ? 'is-open' : ''}`} />
      <aside
        className={[
          'sensor-switch-panel chat-sidebar flex h-full min-h-0 flex-col transition-all duration-300 ease-in-out',
          sidebarOpen ? 'is-open w-full opacity-100 mr-0' : 'is-closed w-0 opacity-0 overflow-hidden p-0 border-0 pointer-events-none mr-0',
        ].join(' ')}
      >
        <div className="panel-head chat-sidebar-head mb-3">
          <div className="flex items-center gap-1.5">
            <span className="text-xl">💬</span>
            <h1 className="font-dot text-lg font-bold text-grass">{sidebarTitle}</h1>
          </div>
          <button
            type="button"
            onClick={newSession}
            className="rounded-full border-2 border-grass bg-grass/10 px-3 py-1.5 font-dot text-xs font-bold text-grass transition-all hover:bg-grass/20 active:scale-95"
          >
            + 새 대화
          </button>
        </div>

        <div className="panel-body chat-scrollbar flex min-h-0 flex-1 flex-col gap-2 overflow-y-auto pr-1">
          {sessions.map((session) => (
            <div
              key={session.session_id}
              onClick={() => void selectSession(session.session_id)}
              className={[
                'group flex cursor-pointer items-center justify-between gap-2 rounded-xl border-2 p-3 text-left transition-all active:scale-[0.99]',
                session.session_id === sessionId
                  ? 'border-grass bg-grass/15 shadow-sm'
                  : 'border-bark/15 bg-white/60 hover:border-grass/50',
              ].join(' ')}
            >
              <div className="flex min-w-0 flex-1 items-start gap-3">
                <div className="chat-session-icon">
                  <img src="/images/incoming/marimo-small.png" alt="" />
                </div>
                <div className="min-w-0 flex-1">
                  <div className="truncate font-dot text-xs font-bold text-bark">{session.title || '새 대화'}</div>
                  <div className="mt-1 truncate font-dot text-[10px] text-bark/50">{session.preview || session.session_id}</div>
                  <div className="mt-1 text-[8px] font-dot text-bark/40">
                    {session.last_message_at ? new Date(session.last_message_at).toLocaleDateString('ko-KR') : ''}
                  </div>
                </div>
              </div>
              <button
                type="button"
                onClick={(event) => void handleDeleteSession(session.session_id, event)}
                className="pointer-events-none flex-shrink-0 rounded-full border-2 border-heart-red bg-heart-red/10 p-1.5 text-heart-red opacity-0 transition-all duration-150 hover:bg-heart-red/20 active:scale-90 group-hover:opacity-100 group-hover:pointer-events-auto group-focus-within:pointer-events-auto group-focus-within:opacity-100"
                title="대화 삭제"
              >
                <TrashIcon />
              </button>
            </div>
          ))}

          {sessions.length === 0 && (
            <div className="py-8 text-center font-dot text-xs text-bark/40">아직 대화가 없습니다.</div>
          )}
        </div>
      </aside>

      <section className="sensor-switch-panel chat-panel flex h-full min-h-0 flex-1 flex-col overflow-hidden">
        <div className="panel-head chat-session-header mb-3 flex flex-wrap items-center justify-between gap-2">
          <div className="flex items-center gap-2.5">
            <button
              type="button"
              onClick={() => setSidebarOpen(!sidebarOpen)}
              className="inline-flex h-10 w-10 items-center justify-center rounded-full border-2 border-grass bg-grass/10 text-grass shadow-sm transition-all hover:bg-grass/20 active:scale-95"
              title={sidebarOpen ? '사이드바 닫기' : '사이드바 열기'}
              aria-label={sidebarOpen ? '사이드바 닫기' : '사이드바 열기'}
            >
              <SidebarToggleIcon open={sidebarOpen} />
            </button>
            <div className="flex flex-col">
              <div className="font-dot text-[10px] font-bold uppercase tracking-[0.18em] text-bark/45">대화 제목</div>
              <div className="font-dot text-lg font-bold text-bark">{sessionTitle}</div>
            </div>
          </div>
        </div>

        <div className="panel-body flex min-h-0 flex-1 flex-col gap-3 overflow-hidden">
          {error && (
            <div className="rounded-xl border-2 border-heart-red bg-heart-red/10 p-3 font-dot text-xs text-heart-red animate-bounce">
              오류: {error}
            </div>
          )}

          {actionNote && (
            <div className="flex items-center gap-2 rounded-xl border-2 border-gold bg-gold/10 p-2.5 font-dot text-xs text-bark">
              <span className="text-sm">📌</span>
              <div>
                <span className="font-bold text-gold-dark">최근 상태 반영:</span> {actionNote}
              </div>
            </div>
          )}

          <div ref={feedRef} className="chat-feed chat-scrollbar flex-1 min-h-0 overflow-y-auto rounded-2xl border border-bark/10 bg-white/40 p-4">
            <div className="flex flex-col gap-4">
              {orderedMessages.map((message) => {
              const isUser = message.role === 'user';
              const text = sanitizeMessageContent(message.content);

              return (
                <div
                  key={message.message_id}
                  className={`flex max-w-[85%] gap-3 ${isUser ? 'self-end flex-row-reverse' : 'self-start'}`}
                >
                  <div
                    className={[
                      'flex h-9 w-9 flex-shrink-0 items-center justify-center overflow-hidden rounded-xl border-2 font-dot text-xs font-bold shadow-sm transition-transform hover:scale-110',
                      isUser ? 'border-sky bg-sky/20 text-sky' : 'border-grass bg-grass/20 text-grass',
                    ].join(' ')}
                  >
                    {isUser ? '나' : <img src="/images/incoming/marimo-small.png" alt="마리모" className="h-7 w-7 object-contain" />}
                  </div>

                  <div className="flex flex-col text-left">
                    <div className={isUser ? 'chat-bubble-player' : 'speech-bubble'}>
                      <div className="whitespace-pre-wrap font-dot text-sm leading-relaxed text-bark">
                        {text}
                      </div>
                    </div>

                    {isUser ? (
                      <div className="mt-1.5 flex items-center justify-end gap-2 text-[9px] font-dot text-bark/40">
                        <span>{formatClock(message.created_at)}</span>
                      </div>
                    ) : (
                      <div className="mt-1.5 flex items-center gap-2 text-[9px] font-dot text-bark/40">
                        <button
                          type="button"
                          onClick={() => void play(text)}
                          className="chat-message-action inline-flex h-8 w-8 items-center justify-center rounded-full transition-all hover:scale-105 active:scale-95"
                          aria-label="음성 듣기"
                          title="음성 듣기"
                        >
                          <PlayIcon />
                        </button>
                        <button
                          type="button"
                          onClick={() => void copyText(text)}
                          className="chat-message-action inline-flex h-8 w-8 items-center justify-center rounded-full transition-all hover:scale-105 active:scale-95"
                          aria-label="복사"
                          title="복사"
                        >
                          <CopyIcon />
                        </button>
                      </div>
                    )}
                  </div>
                </div>
              );
              })}

              {busy && (
                <div className="flex max-w-[85%] gap-3 self-start">
                  <div className="chat-session-icon overflow-hidden">
                    <img src="/images/incoming/marimo-small.png" alt="마리모" />
                  </div>
                  <div className="chat-thinking-bubble">
                    <div className="speech-bubble">
                      <div className="chat-thinking-bubble__label font-dot">마리모가 답변을 생각 중...</div>
                      <div className="chat-thinking-bubble__dots" aria-hidden="true">
                        <span />
                        <span />
                        <span />
                      </div>
                    </div>
                  </div>
                </div>
              )}

              {!detail && !busy && (
                <div className="flex flex-col items-center justify-center py-20 text-center">
                  <div className="mb-3 text-4xl animate-bounce">💬</div>
                  <div className="mb-1 font-dot text-sm font-bold text-grass">안녕하세요! 먼저 대화를 시작해 주세요.</div>
                  <div className="max-w-sm font-dot text-xs text-bark/50">
                    아래 입력창에 글을 적거나 마이크 버튼을 눌러 보세요. 음성으로 대화하고 싶은 경우에도 바로 응답합니다.
                  </div>
                </div>
              )}
            </div>
          </div>

          <div className="mt-4 relative">
            <div className="chat-input-shell relative flex items-center gap-2 rounded-full border-2 border-bark/30 bg-white/95 px-4 py-2 shadow-md transition-all duration-200 hover:border-grass focus-within:border-grass focus-within:ring-2 focus-within:ring-grass/20">
              <button
                type="button"
                onClick={recording ? stopVoiceInput : startVoiceInput}
                className={[
                  'flex h-11 w-11 items-center justify-center rounded-full border-2 text-sm transition-all duration-200 active:scale-90',
                  recording
                    ? 'border-heart-red bg-heart-red/15 text-heart-red animate-pulse'
                    : 'border-sky bg-sky/10 text-sky hover:bg-sky/20 shadow-sm',
                ].join(' ')}
              title={recording ? '음성 입력 중지' : '음성 입력'}
            >
              <MicIcon />
            </button>

            <input
              className="chat-input flex-1 border-0 bg-transparent px-2 font-dot text-sm text-bark outline-none placeholder-bark/30 disabled:opacity-50"
              value={input}
              onChange={(event) => setInput(event.target.value)}
              onKeyDown={(event) => {
                if (event.key === 'Enter') void send();
                }}
                placeholder="마리모에게 질문하거나 명령을 입력해 보세요..."
                disabled={busy}
              />

            <button
              type="button"
              onClick={() => void send()}
              disabled={busy || !input.trim()}
              className="chat-send-button flex h-11 w-11 items-center justify-center rounded-full border-2 border-grass bg-grass/15 font-bold text-grass transition-all duration-200 hover:scale-105 hover:bg-grass/25 active:scale-95 disabled:pointer-events-none disabled:opacity-30"
            >
              →
            </button>
          </div>
        </div>
        </div>
      </section>
    </div>
  );
}

