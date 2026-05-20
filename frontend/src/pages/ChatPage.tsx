import { useEffect, useRef, useState } from 'react';
import { askChat, getSessionDetail, listSessions, synthesizeTts, updateRuntimeSettings, deleteSession, type SessionDetail, type SessionSummary } from '../api';
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

  const handleDeleteSession = async (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    if (!window.confirm('이 대화 기록을 정말 삭제하시겠습니까?')) return;
    try {
      await deleteSession(id);
      if (sessionId === id) {
        setSessionId(undefined);
        setDetail(null);
        setActionNote('');
        await refreshSessions();
      } else {
        await refreshSessions(sessionId);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : '대화 삭제 실패');
    }
  };


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
    feedRef.current?.scrollTo({
      top: feedRef.current.scrollHeight,
      behavior: 'smooth'
    });
  }, [detail]);

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
    try {
      await updateRuntimeSettings({ distance_inside_threshold: false });
    } catch {
      // background fail ignore
    }
  };

  const send = async (text = input) => {
    const value = text.trim();
    if (!value || busy) return;
    setBusy(true);
    setError('');
    setActionNote('');
    try {
      const result = await askChat(value, sessionId);
      const nextId = result.session_id;
      setInput('');
      const action = result.action_result;
      if (action?.summary) {
        let note = action.summary;
        if (action.patch && 'web_voice_enabled' in action.patch) {
          note = `웹 음성 ${action.patch.web_voice_enabled ? '켜짐' : '꺼짐'} / ${note}`;
        }
        setActionNote(note);
      }
      await refreshSessions(nextId);
    } catch (e) {
      setError(e instanceof Error ? e.message : '전송에 실패했습니다.');
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

  const play = async (text: string) => {
    try {
      const blob = await synthesizeTts(text);
      const url = URL.createObjectURL(blob);
      const audio = new Audio(url);
      audio.onended = () => URL.revokeObjectURL(url);
      await audio.play();
    } catch (e) {
      setError(e instanceof Error ? e.message : '음성 재생 실패');
    }
  };

  return (
    <div className={`grid h-[calc(100vh-160px)] gap-4 overflow-hidden transition-all duration-300 ${sidebarOpen ? 'lg:grid-cols-[280px_1fr]' : 'lg:grid-cols-[0px_1fr]'}`}>
      {/* 1. 사이드바 (좌측 세션 목록) */}
      <aside className={[
        'pixel-card flex h-full flex-col min-h-0 transition-all duration-300 ease-in-out',
        sidebarOpen ? 'w-full opacity-100 mr-0' : 'w-0 opacity-0 overflow-hidden p-0 border-0 pointer-events-none mr-0'
      ].join(' ')}>
        <div className="mb-3 flex items-center justify-between gap-2 border-b border-bark/10 pb-2">
          <div className="flex items-center gap-1.5">
            <span className="text-xl">💬</span>
            <h1 className="font-pixel text-lg text-grass">대화 기록</h1>
          </div>
          <button 
            type="button"
            onClick={newSession} 
            className="rounded-lg border-2 border-grass bg-grass/10 px-2.5 py-1 font-pixel text-xs text-grass hover:bg-grass/20 active:scale-95 transition-all"
          >
            + 새 대화
          </button>
        </div>
        
        {/* 세션 리스트 스크롤 영역 */}
        <div className="flex-1 overflow-y-auto min-h-0 pr-1 flex flex-col gap-2">
          {sessions.map((session) => (
            <div
              key={session.session_id}
              onClick={() => void selectSession(session.session_id)}
              className={[
                'rounded-xl border-2 p-3 text-left transition-all active:scale-[0.99] cursor-pointer flex justify-between items-center gap-2 group',
                session.session_id === sessionId ? 'border-grass bg-grass/15 shadow-sm' : 'border-bark/15 bg-white/60 hover:border-grass/50',
              ].join(' ')}
            >
              <div className="flex-1 min-w-0">
                <div className="font-dot text-xs font-bold text-bark truncate">{session.title || 'New Chat'}</div>
                <div className="mt-1 truncate font-dot text-[10px] text-bark/50">{session.preview || session.session_id}</div>
                <div className="mt-1 text-[8px] font-dot text-bark/40">
                  {session.last_message_at ? new Date(session.last_message_at).toLocaleDateString('ko-KR') : ''}
                </div>
              </div>
              <button
                type="button"
                onClick={(e) => void handleDeleteSession(session.session_id, e)}
                className="p-1.5 rounded-lg border-2 border-heart-red bg-heart-red/10 text-heart-red hover:bg-heart-red/20 active:scale-90 transition-all flex-shrink-0 opacity-0 group-hover:opacity-100 focus:opacity-100 duration-200"
                title="대화 삭제"
              >
                🗑️
              </button>
            </div>
          ))}

          {sessions.length === 0 && (
            <div className="py-8 text-center font-dot text-xs text-bark/40">
              이전 대화가 없습니다.
            </div>
          )}
        </div>
      </aside>

      {/* 2. 메인 대화 세션 */}
      <section className="pixel-card flex h-full flex-col min-h-0 flex-1">
        {/* 헤더 영역 */}
        <div className="mb-3 flex flex-wrap items-center justify-between gap-2 border-b border-bark/10 pb-3">
          <div className="flex items-center gap-2.5">
            <button
              type="button"
              onClick={() => setSidebarOpen(!sidebarOpen)}
              className="rounded-lg border-2 border-grass bg-grass/10 px-3 py-1.5 font-dot text-xs font-bold text-grass hover:bg-grass/20 active:scale-95 transition-all shadow-sm"
            >
              {sidebarOpen ? '◀ 접기' : '▶ 세션 목록'}
            </button>
            <div className="flex items-center gap-2">
              <div>
                <div className="font-pixel text-sm text-bark">
                  {sessionId ? `세션: ${sessionId.slice(0, 8)}...` : '새로운 대화'}
                </div>
                <div className="font-dot text-[10px] text-bark/50">
                  실시간 픽셀아트 마리모 보이스 에이전트 연동 중
                </div>
              </div>
              {sessionId && (
                <button
                  type="button"
                  onClick={(e) => void handleDeleteSession(sessionId, e)}
                  className="rounded-lg border-2 border-heart-red bg-heart-red/10 px-2.5 py-1 font-pixel text-xs text-heart-red hover:bg-heart-red/20 active:scale-95 transition-all shadow-sm flex items-center gap-1.5 ml-2"
                  title="대화 삭제"
                >
                  🗑️ 대화 삭제
                </button>
              )}
            </div>
          </div>
          {/* 상태 배지 */}
          <div className="flex items-center gap-2">
            <span className="h-2.5 w-2.5 rounded-full bg-grass animate-ping" />
            <span className="font-dot text-[10px] text-grass font-bold border-2 border-grass/30 rounded-full px-2 py-0.5 bg-grass/5">
              ONLINE
            </span>
          </div>
        </div>

        {/* 에러 피드백 */}
        {error && (
          <div className="mb-3 rounded-xl border-2 border-heart-red bg-heart-red/10 p-3 font-dot text-xs text-heart-red animate-bounce">
            ⚠️ {error}
          </div>
        )}

        {/* 마지막 하드웨어 액션 내역 */}
        {actionNote && (
          <div className="mb-3 flex items-center gap-2 rounded-xl border-2 border-gold bg-gold/10 p-2.5 font-dot text-xs text-bark">
            <span className="text-sm">⚙️</span>
            <div>
              <span className="font-bold text-gold-dark">최근 하드웨어 명령:</span> {actionNote}
            </div>
          </div>
        )}

        {/* 3. 대화 피드 스크롤 영역 (ChatGPT 스타일) */}
        <div ref={feedRef} className="flex-1 overflow-y-auto rounded-2xl bg-white/40 p-4 border border-bark/10 min-h-0">
          <div className="flex flex-col gap-4">
            {orderedMessages.map((message) => {
              const isUser = message.role === 'user';
              return (
                <div key={message.message_id} className={`flex gap-3 max-w-[85%] ${isUser ? 'self-end flex-row-reverse' : 'self-start'}`}>
                  {/* 말풍선 좌측/우측 픽셀아트 프로필 아바타 */}
                  <div className={[
                    'w-8 h-8 rounded-lg border-2 flex items-center justify-center font-pixel text-sm flex-shrink-0 shadow-sm transition-transform hover:scale-110',
                    isUser ? 'border-sky bg-sky/20 text-sky' : 'border-grass bg-grass/20 text-grass'
                  ].join(' ')}>
                    {isUser ? '👤' : '🌿'}
                  </div>

                  {/* 실제 대화 말풍선 */}
                  <div className="flex flex-col text-left">
                    <div className={isUser ? 'chat-bubble-player' : 'speech-bubble'}>
                      <div className="whitespace-pre-wrap font-dot text-sm leading-relaxed text-bark">
                        {sanitizeMessageContent(message.content)}
                      </div>
                    </div>
                    {/* 메타데이터 및 tts 듣기 버튼 */}
                    <div className={`mt-1.5 flex items-center gap-2 text-[9px] font-dot text-bark/40 ${isUser ? 'justify-end' : 'justify-start'}`}>
                      <span>
                        {message.meta?.source ? String(message.meta.source) : message.role}
                      </span>
                      <span>·</span>
                      <span>
                        {new Date(message.created_at).toLocaleTimeString('ko-KR', { hour: '2-digit', minute: '2-digit' })}
                      </span>
                      {!isUser && (
                        <>
                          <span>·</span>
                          <button onClick={() => void play(sanitizeMessageContent(message.content))} className="tts-btn flex items-center gap-0.5 px-1.5 py-0.5 rounded font-pixel hover:scale-105 active:scale-95 transition-all">
                            🔊 듣기
                          </button>
                        </>
                      )}
                    </div>
                  </div>
                </div>
              );
            })}
            {!detail && (
              <div className="flex flex-col items-center justify-center py-20 text-center">
                <div className="text-4xl animate-bounce mb-3">🌿</div>
                <div className="font-pixel text-sm text-grass mb-1">안녕! 나는 반려식물 마리모야!</div>
                <div className="font-dot text-xs text-bark/50 max-w-sm">
                  하단 입력창에 글을 작성하거나 마이크 버튼을 눌러 나에게 음성으로 대화를 건네봐! 하드웨어 단독 모드에서도 실시간 응답할 수 있어.
                </div>
              </div>
            )}
          </div>
        </div>

        {/* 4. 하단 플로팅 캡슐형 입력창 (ChatGPT/Gemini 모방 디자인) */}
        <div className="mt-4 relative">
          <div className="relative flex items-center gap-2 rounded-full border-2 border-bark/30 bg-white/95 pl-4 pr-2 py-2 hover:border-grass focus-within:border-grass focus-within:ring-2 focus-within:ring-grass/20 shadow-md transition-all duration-200">
            {/* 4-1. 음성 입력 토글 마이크 버튼 */}
            <button
              type="button"
              onClick={recording ? stopVoiceInput : startVoiceInput}
              className={[
                'w-9 h-9 rounded-full border-2 flex items-center justify-center text-sm transition-all duration-200 active:scale-90',
                recording 
                  ? 'border-heart-red bg-heart-red/15 text-heart-red animate-pulse' 
                  : 'border-sky bg-sky/10 text-sky hover:bg-sky/20'
              ].join(' ')}
              title={recording ? '녹음 중지' : '음성 입력'}
            >
              🎤
            </button>

            {/* 4-2. 텍스트 입력 Input */}
            <input
              className="flex-1 bg-transparent border-0 outline-none font-dot text-sm text-bark px-2 placeholder-bark/30 disabled:opacity-50"
              value={input}
              onChange={(event) => setInput(event.target.value)}
              onKeyDown={(event) => {
                if (event.key === 'Enter') void send();
              }}
              placeholder="마리모에게 질문하거나 명령을 내려보세요..."
              disabled={busy}
            />

            {/* 4-3. 전송 버튼 */}
            <button
              type="button"
              onClick={() => void send()}
              disabled={busy || !input.trim()}
              className="w-9 h-9 rounded-full border-2 border-grass bg-grass/15 text-grass flex items-center justify-center font-bold hover:bg-grass/25 hover:scale-105 active:scale-95 disabled:opacity-30 disabled:pointer-events-none transition-all duration-200"
            >
              ➔
            </button>
          </div>
          {/* 플로팅 안내문구 */}
          <div className="text-center font-dot text-[9px] text-bark/40 mt-1.5">
            마리모는 하드웨어 센서 데이터를 읽으며 최적의 자연어 처리를 이행합니다.
          </div>
        </div>
      </section>
    </div>
  );
}
