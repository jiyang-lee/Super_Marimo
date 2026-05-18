import { useRef, useEffect } from 'react';
import { PixelMarimo } from '../PixelMarimo';
import { PixelButton } from '../components/PixelButton';

interface Msg { role: 'player' | 'npc'; content: string; meta?: string }

interface Props {
  msgs: Msg[];
  voiceOk: boolean;
  llmOk: boolean;
  isRecording: boolean;
  busy: boolean;
  input: string;
  setInput: (v: string) => void;
  startRec: () => void;
  stopRec: () => void;
  sendText: () => void;
  playTts: (text: string) => void;
}

export function ChatPage({
  msgs, voiceOk, llmOk, isRecording, busy, input, setInput, startRec, stopRec, sendText, playTts
}: Props) {
  const chatRef = useRef<HTMLDivElement>(null);
  useEffect(() => { chatRef.current?.scrollTo(0, chatRef.current.scrollHeight); }, [msgs]);

  return (
    <div className="flex flex-col flex-1 min-h-0">
      <div className="flex items-center gap-2 mb-2 px-1">
        <span className="font-dot text-xs text-bark/60">
          {voiceOk ? '🎤 VOICE OK' : '🎤 VOICE NG'} &nbsp;
          {llmOk ? '🧠 LLM OK' : '🧠 LLM NG'}
        </span>
      </div>
      <div ref={chatRef} className="flex-1 overflow-y-auto p-2 flex flex-col gap-2" style={{ scrollbarWidth: 'none' }}>
        {msgs.map((m, i) => (
          <div key={i} className={`flex gap-2 ${m.role === 'player' ? 'self-end flex-row-reverse' : 'self-start'}`}>
            {m.role === 'npc' && <PixelMarimo size={32} />}
            <div className={m.role === 'npc' ? 'chat-bubble-npc' : 'chat-bubble-player'} style={{ maxWidth: '260px' }}>
              <p className="font-dot text-sm whitespace-pre-wrap">{m.content}</p>
              {m.meta && <div className="msg-time">{m.meta}</div>}
              {m.role === 'npc' && m.content && (
                <button className="tts-btn mt-1" onClick={() => playTts(m.content)}>▶ 듣기</button>
              )}
            </div>
          </div>
        ))}
      </div>
      <div className="bg-parchment/80 border-t-2 border-bark p-2 flex gap-2 items-center">
        <input
          className="pixel-input text-sm"
          type="text" placeholder="메시지 입력..."
          value={input} onChange={e => setInput(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && sendText()} disabled={busy}
        />
        <button className={`icon-mic ${isRecording ? 'recording' : ''}`}
          onMouseDown={startRec} onMouseUp={stopRec} onMouseLeave={stopRec}
          onTouchStart={e => { e.preventDefault(); startRec(); }} onTouchEnd={e => { e.preventDefault(); stopRec(); }}
          disabled={busy}>🎤</button>
        <PixelButton onClick={() => sendText()} disabled={busy} size="sm">▶</PixelButton>
      </div>
    </div>
  );
}
