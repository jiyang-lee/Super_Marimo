const AGENT = import.meta.env.VITE_AGENT_BASE_URL ?? '/agent';
const API = import.meta.env.VITE_API_BASE_URL ?? '/api';
const VOICE = import.meta.env.VITE_VOICE_BASE_URL ?? '/voice';
const LLM = import.meta.env.VITE_LLM_BASE_URL ?? '/llm';

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
  answer?: string;
  llm_answer?: string;
  tts_text?: string;
  stt_text?: string;
  session_id: string;
  api_health?: { ok: boolean; data?: unknown; error?: string };
  tts_ok?: boolean;
  tts_path?: string | null;
  interaction_id?: number | null;
  session_created?: boolean | null;
  messages_saved?: number | null;
  runtime_settings?: RuntimeSettings;
  session_summary?: string;
  action_result?: {
    action_type?: string;
    summary?: string;
    patch?: Record<string, unknown>;
    before?: Record<string, unknown> | null;
    after?: { settings?: RuntimeSettings } | null;
  } | null;
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
  rag?: string;
  alerts?: string[];
}

export interface SensorLatest {
  latest_realtime: SensorReading | null;
  latest_merged: SensorReading | null;
  runtime_settings?: RuntimeSettings;
  distance_inside_threshold?: boolean;
}

export interface RuntimeSettings {
  distance_detection_enabled: boolean;
  wake_enabled: boolean;
  web_voice_enabled: boolean;
  distance_threshold_cm: number;
  distance_inside_threshold: boolean;
  updated_at?: string;
}

export interface DeviceEvent {
  event_id: number;
  event_type: string;
  device_id: string;
  trigger_source: string;
  generated_text: string;
  played: boolean;
  status?: string;
  created_at: string;
  distance: number | null;
  state_level: string;
  [key: string]: unknown;
}

export async function listEvents(options?: { event_type?: string; played?: boolean; limit?: number; offset?: number }): Promise<{ events: DeviceEvent[]; count: number; limit: number; offset: number }> {
  const params = new URLSearchParams();
  if (options?.event_type) params.append('event_type', options.event_type);
  if (options?.played !== undefined) params.append('played', String(options.played));
  if (options?.limit !== undefined) params.append('limit', String(options.limit));
  if (options?.offset !== undefined) params.append('offset', String(options.offset));
  return fetchJson(`${API}/events?${params.toString()}`);
}

export async function markEventPlayed(eventId: number): Promise<DeviceEvent> {
  return fetchJson(`${API}/events/${eventId}/played`, { method: 'POST' });
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

export async function deleteSession(sessionId: string): Promise<{ deleted: boolean; session_id: string }> {
  return fetchJson<{ deleted: boolean; session_id: string }>(`${API}/sessions/${sessionId}`, {
    method: 'DELETE',
  });
}


export async function getLatestSensor(): Promise<SensorLatest> {
  return fetchJson<SensorLatest>(`${API}/sensor/latest`);
}

export async function getSensorHistory(limit = 24): Promise<{ realtime_history: SensorReading[]; hourly_history: SensorReading[] }> {
  return fetchJson(`${API}/sensor/history?limit=${limit}`);
}

export async function getRuntimeSettings(): Promise<{ settings: RuntimeSettings }> {
  return fetchJson(`${API}/sensor/runtime-settings`);
}

export async function updateRuntimeSettings(patch: Partial<RuntimeSettings>): Promise<{ settings: RuntimeSettings }> {
  return fetchJson(`${API}/sensor/runtime-settings`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(patch),
  });
}

export interface RuntimeSettingsHistory {
  history_id: number;
  setting_key: string;
  previous_value: Record<string, unknown> | null;
  new_value: Record<string, unknown>;
  changed_by: string | null;
  changed_at: string;
  action_type: string | null;
  summary: string | null;
}

export async function getRuntimeSettingsHistory(limit = 20): Promise<{ history: RuntimeSettingsHistory[]; limit: number }> {
  return fetchJson(`${API}/sensor/runtime-settings/history?limit=${limit}`);
}

export async function ingestRealtimeSensor(payload: { light: number; distance: number }): Promise<unknown> {
  return fetchJson(`${API}/sensor/realtime-ingest`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
}

export async function askChat(text: string, sessionId?: string, isTest?: boolean): Promise<AskResult> {
  return fetchJson<AskResult>(`${API}/ask`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      question: text,
      session_id: sessionId ?? null,
      use_sensor_context: true,
      is_test: isTest ?? null,
    }),
  });
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
