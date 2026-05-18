const AGENT = '/agent';
const API = '/api';
const VOICE = '/voice';
const LLM = '/llm';

async function fetchJson<T>(url: string, init?: RequestInit): Promise<T> {
  const response = await fetch(url, {
    ...init,
    headers: {
      Accept: 'application/json',
      ...(init?.headers ?? {}),
    },
  });

  const raw = await response.text();
  const data = raw ? safeParseJson(raw) : null;

  if (!response.ok) {
    const detail =
      data && typeof data === 'object'
        ? String((data as Record<string, unknown>).detail ?? (data as Record<string, unknown>).error ?? response.statusText)
        : raw || response.statusText;
    throw new Error(detail);
  }

  return data as T;
}

function safeParseJson(raw: string): unknown {
  try {
    return JSON.parse(raw) as unknown;
  } catch {
    return raw;
  }
}

export interface ServiceHealth {
  ok: boolean;
  [key: string]: unknown;
}

export interface AgentHealth {
  ok: boolean;
  server: string;
  session_id: string | null;
  api_server: ServiceHealth;
  default_stt_model: string;
}

export interface ApiHealth extends ServiceHealth {
  server: string;
  llm_server_url: string;
  db?: {
    configured?: boolean;
    ok?: boolean;
    error?: string;
  };
}

export interface VoiceHealth extends ServiceHealth {
  server: string;
  mock_mode: boolean;
  stt_models: Record<string, { loaded: boolean; device: string | null; compute_type: string | null; size: string }>;
  stt_device: string;
  stt_compute_type: string;
  tts_backend: string;
  tts_model: string;
  tts_voice_name: string;
  tts_voice_names: string[];
  tts_lang: string;
  tts_ready: boolean;
  tts_runtime_voice_name: string;
  tts_error: string | null;
  tts_cache_dir: string;
  tts_model_dir: string;
}

export interface LlmHealth extends ServiceHealth {
  server: string;
  mock_mode: boolean;
  model: string;
  revision: string;
  framework: string;
  model_loaded: boolean;
  cuda_available: boolean;
  device: string | null;
  mode: string;
  error: string | null;
  error_type: string | null;
}

export interface AskResult {
  saved: boolean;
  answer: string;
  session_id: string;
  api_health?: { ok: boolean; data?: unknown; error?: string };
  tts_ok: boolean;
  tts_path?: string | null;
  interaction_id?: number | null;
  session_created?: boolean | null;
  messages_saved?: number | null;
}

export interface AskAgentOptions {
  personaMemo?: string;
  systemMemo?: string;
  voiceName?: string;
  speak?: boolean;
}

export interface SessionSummary {
  session_id: string;
  created_at: string;
  last_seen_at: string;
  ended_at: string | null;
  turn_count: number;
  message_count: number;
  title: string;
  preview: string;
  last_message_at: string | null;
}

export interface SessionMessage {
  message_id: number;
  session_id: string;
  role: string;
  content: string;
  created_at: string;
  meta: Record<string, unknown>;
}

export interface SessionDetail {
  session: {
    session_id: string;
    created_at: string;
    last_seen_at: string;
    ended_at: string | null;
    turn_count: number;
    meta: Record<string, unknown>;
  };
  messages: SessionMessage[];
}

export interface SensorReading {
  reading_id?: number;
  created_at?: string;
  sensor_type?: string;
  temperature?: number;
  humidity?: number;
  light?: number;
  water_level?: number;
  distance?: number;
  state_level?: string;
  alerts?: string[];
}

export interface SensorLatest {
  latest_realtime: SensorReading | null;
  latest_hourly: SensorReading | null;
  latest_merged: SensorReading | null;
}

export async function checkAgentHealth(): Promise<AgentHealth> {
  return fetchJson<AgentHealth>(`${AGENT}/health`);
}

export async function checkApiHealth(): Promise<ApiHealth> {
  return fetchJson<ApiHealth>(`${API}/health`);
}

export async function checkVoiceHealth(): Promise<VoiceHealth> {
  return fetchJson<VoiceHealth>(`${VOICE}/health`);
}

export async function checkLlmHealth(): Promise<LlmHealth> {
  return fetchJson<LlmHealth>(`${LLM}/health`);
}

export async function listSessions(limit = 5): Promise<SessionSummary[]> {
  const data = await fetchJson<{ sessions: SessionSummary[] }>(`${API}/sessions?limit=${limit}`);
  return data.sessions ?? [];
}

export async function getSessionDetail(sessionId: string): Promise<SessionDetail> {
  return fetchJson<SessionDetail>(`${API}/sessions/${sessionId}`);
}

export async function getLatestSensor(): Promise<SensorLatest> {
  return fetchJson<SensorLatest>(`${API}/sensor/latest`);
}

export async function askAgent(text: string, sessionId?: string, options?: AskAgentOptions): Promise<AskResult> {
  return fetchJson<AskResult>(`${AGENT}/ask`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      text,
      session_id: sessionId ?? null,
      speak: options?.speak ?? false,
      persona_memo: options?.personaMemo ?? null,
      system_memo: options?.systemMemo ?? null,
      voice_name: options?.voiceName ?? null,
    }),
  });
}

export async function synthesizeTts(text: string, voiceName?: string): Promise<Blob> {
  const response = await fetch(`${VOICE}/tts`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', Accept: 'audio/wav' },
    body: JSON.stringify({
      text,
      voice_name: voiceName ?? null,
    }),
  });

  if (!response.ok) {
    const raw = await response.text();
    throw new Error(raw || response.statusText);
  }

  return response.blob();
}
