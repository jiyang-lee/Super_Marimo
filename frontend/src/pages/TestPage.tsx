import { useState } from 'react';
import { askAgent, synthesizeTts } from '../api';

const PERSONA_PRESETS = [
  { id: 'kid', label: '꼬마 기본', memo: '한국인 꼬마 같은 말투를 쓰되 예의 바르고 다정하게 말한다. 짧고 자연스럽게 답하고, 너무 유치하지 않게 부드러운 톤을 유지한다.' },
  { id: 'bright', label: '밝은 꼬마', memo: '밝고 명랑한 한국인 꼬마 느낌으로 말하되 예의 바르고 친절하게 답한다. 짧고 자연스럽게 핵심만 말한다.' },
  { id: 'calm', label: '차분한 꼬마', memo: '차분한 한국인 꼬마 느낌으로 말하되 예의 바르고 부드럽게 답한다. 짧고 자연스럽게 핵심만 말한다.' },
];

export function TestPage() {
  const [text, setText] = useState('');
  const [personaId, setPersonaId] = useState('kid');
  const [answer, setAnswer] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [sessionId, setSessionId] = useState<string | undefined>(undefined);

  const persona = PERSONA_PRESETS.find((p) => p.id === personaId);

  const send = async () => {
    if (!text.trim() || loading) return;
    setLoading(true);
    setError('');
    setAnswer('');
    try {
      const result = await askAgent(text, sessionId, {
        personaMemo: persona?.memo,
        speak: false,
      });
      setAnswer(result.answer || '');
      setSessionId(result.session_id);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'ask failed');
    } finally {
      setLoading(false);
    }
  };

  const playTts = async () => {
    if (!answer) return;
    try {
      const blob = await synthesizeTts(answer);
      const url = URL.createObjectURL(blob);
      const audio = new Audio(url);
      await audio.play();
      audio.onended = () => URL.revokeObjectURL(url);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'tts failed');
    }
  };

  return (
    <div className="flex flex-col gap-4">
      <h1 className="font-pixel text-xl text-grass">Manual Test</h1>

      <div className="pixel-card space-y-3">
        <div>
          <div className="mb-1 font-dot text-xs text-bark/60">Persona</div>
          <div className="flex flex-wrap gap-2">
            {PERSONA_PRESETS.map((p) => (
              <button
                key={p.id}
                onClick={() => setPersonaId(p.id)}
                className={[
                  'rounded-lg border-2 px-3 py-1 font-dot text-xs transition',
                  personaId === p.id
                    ? 'border-grass bg-grass/15 text-grass'
                    : 'border-bark/30 bg-white/50 text-bark',
                ].join(' ')}
              >
                {p.label}
              </button>
            ))}
          </div>
          <div className="mt-2 rounded bg-white/50 p-2 font-dot text-xs text-bark/80">
            {persona?.memo}
          </div>
        </div>

        <div>
          <div className="mb-1 font-dot text-xs text-bark/60">Message</div>
          <input
            type="text"
            value={text}
            onChange={(e) => setText(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && send()}
            className="pixel-input w-full"
            placeholder="Say something to Marimo..."
          />
        </div>

        <div className="flex gap-2">
          <button
            onClick={send}
            disabled={loading}
            className="rounded-lg border-2 border-grass bg-grass/15 px-4 py-2 font-dot text-xs text-grass hover:bg-grass/25 disabled:opacity-50"
          >
            {loading ? 'sending...' : 'send'}
          </button>
          {sessionId && (
            <span className="self-center font-dot text-[10px] text-bark/50">
              session {sessionId.slice(0, 8)}
            </span>
          )}
        </div>

        {error && (
          <div className="rounded-lg border-2 border-heart-red bg-heart-red/10 p-2 font-dot text-xs text-heart-red">
            {error}
          </div>
        )}

        {answer && (
          <div className="space-y-2">
            <div className="rounded-lg border border-bark/20 bg-white/70 p-3 font-dot text-sm text-bark">
              {answer}
            </div>
            <button
              onClick={playTts}
              className="rounded-lg border-2 border-sky bg-sky/15 px-3 py-1 font-dot text-xs text-sky hover:bg-sky/25"
            >
              play TTS
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
