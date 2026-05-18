const AGENT = '/agent';

export interface AgentHealth {
  ok: boolean;
  server: string;
  session_id: string | null;
  api_server?: { ok: boolean; data?: unknown; error?: string };
  voice_server: { ok: boolean; data?: unknown; error?: string };
  llm_server: { ok: boolean; data?: unknown; error?: string };
  default_stt_model: string;
}

export interface AskResult {
  saved: boolean;
  answer: string;
  session_id: string;
  api_health?: { ok: boolean; data?: unknown; error?: string };
  voice_health: { ok: boolean; data?: unknown; error?: string };
  llm_health: { ok: boolean; data?: unknown; error?: string };
  tts_ok: boolean;
  tts_path?: string | null;
  interaction_id?: number | null;
  session_created?: boolean | null;
  messages_saved?: number | null;
}

export async function checkAgentHealth(): Promise<AgentHealth> {
  const r = await fetch(`${AGENT}/health`);
  const d = await r.json();
  if (!r.ok) throw new Error(d.detail || r.statusText);
  return d;
}

export async function askAgent(text: string, sessionId?: string): Promise<AskResult> {
  const r = await fetch(`${AGENT}/ask`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
    body: JSON.stringify({ text, session_id: sessionId ?? null, speak: false }),
  });
  const d = await r.json();
  if (!r.ok) throw new Error(d.detail || r.statusText);
  return d;
}
