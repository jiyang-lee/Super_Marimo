const AGENT = import.meta.env.VITE_AGENT_BASE_URL ?? '/agent';
const API = import.meta.env.VITE_API_BASE_URL ?? '/api';
const VOICE = import.meta.env.VITE_VOICE_BASE_URL ?? '/voice';
const LLM = import.meta.env.VITE_LLM_BASE_URL ?? '/llm';
const VOICE_NAME_STORAGE_KEY = 'super-marimo.voice-name';
const PERSONA_PRESET_STORAGE_KEY = 'super-marimo.persona-preset';
const DEFAULT_TTS_VOICE_NAMES = ['F1', 'F2', 'F3', 'F4', 'F5', 'M1', 'M2', 'M3', 'M4', 'M5'] as const;

export type PersonaPresetId = 'kind' | 'practical' | 'grumpy';

export interface PersonaPreset {
  id: PersonaPresetId;
  label: string;
  description: string;
  memo: string;
}

export const PERSONA_PRESETS: PersonaPreset[] = [
  {
    id: 'kind',
    label: '착하고 다정함',
    description: '부드럽고 배려심 있는 응답',
    memo: '착하고 다정하게 답해줘. 상대의 기분을 먼저 살피고, 짧고 따뜻한 문장으로 말해줘.',
  },
  {
    id: 'practical',
    label: '현실적이고 직관적임',
    description: '군더더기 없이 핵심 위주',
    memo: '현실적이고 직관적으로 답해줘. 불필요한 수식은 줄이고, 바로 실행할 수 있는 핵심만 말해줘.',
  },
  {
    id: 'grumpy',
    label: '툴툴거리고 짜증투성이',
    description: '투덜대지만 내용은 정확',
    memo: '툴툴거리면서도 짜증 섞인 말투로 답해줘. 그래도 필요한 정보는 정확하고 단호하게 전달해줘.',
  },
];

function isPersonaPresetId(value: string): value is PersonaPresetId {
  return PERSONA_PRESETS.some((preset) => preset.id === value);
}

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

export function getStoredVoiceName(fallback = 'F1'): string {
  if (typeof window === 'undefined') return fallback;
  const stored = window.localStorage.getItem(VOICE_NAME_STORAGE_KEY)?.trim();
  return (stored || fallback).toUpperCase();
}

export function setStoredVoiceName(voiceName: string): void {
  if (typeof window === 'undefined') return;
  window.localStorage.setItem(VOICE_NAME_STORAGE_KEY, voiceName.trim().toUpperCase());
}

export function getStoredPersonaPreset(fallback: PersonaPresetId = 'kind'): PersonaPresetId {
  if (typeof window === 'undefined') return fallback;
  const stored = window.localStorage.getItem(PERSONA_PRESET_STORAGE_KEY)?.trim();
  if (stored && isPersonaPresetId(stored)) return stored;
  return fallback;
}

export function setStoredPersonaPreset(presetId: PersonaPresetId): void {
  if (typeof window === 'undefined') return;
  window.localStorage.setItem(PERSONA_PRESET_STORAGE_KEY, presetId);
}

export function resolvePersonaPreset(presetId?: string | null): PersonaPreset {
  const requested = (presetId ?? '').trim();
  const activeId = isPersonaPresetId(requested) ? requested : getStoredPersonaPreset();
  return PERSONA_PRESETS.find((preset) => preset.id === activeId) ?? PERSONA_PRESETS[0];
}

export function getStoredPersonaMemo(): string {
  return resolvePersonaPreset().memo;
}

export function normalizeVoiceNames(names?: string[] | null): string[] {
  const seen = new Set<string>();
  const cleaned = (names ?? [])
    .map((name) => name.trim().toUpperCase())
    .filter(Boolean)
    .filter((name) => {
      if (seen.has(name)) return false;
      seen.add(name);
      return true;
    });

  cleaned.sort((left, right) => {
    const leftMatch = left.match(/^([FM])(\d+)$/);
    const rightMatch = right.match(/^([FM])(\d+)$/);

    if (leftMatch && rightMatch) {
      const leftRank = leftMatch[1] === 'F' ? 0 : 1;
      const rightRank = rightMatch[1] === 'F' ? 0 : 1;
      if (leftRank !== rightRank) return leftRank - rightRank;
      return Number(leftMatch[2]) - Number(rightMatch[2]);
    }

    if (leftMatch) return -1;
    if (rightMatch) return 1;
    return left.localeCompare(right);
  });

  return cleaned.length > 0 ? cleaned : [...DEFAULT_TTS_VOICE_NAMES];
}

export function resolveVoiceNamePreference(availableNames?: string[] | null, fallback = 'F1'): string {
  const options = normalizeVoiceNames(availableNames);
  const stored = getStoredVoiceName(fallback);
  const resolved = options.includes(stored) ? stored : options[0] ?? fallback;
  return resolved.toUpperCase();
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
  session_kind?: string;
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
    session_kind?: string;
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
  water_level_recent_avg_2h?: number;
  light_daytime_avg_13_18?: number;
  light_normalized_0_100?: number;
  water_level_normalized_0_100?: number;
  water_level_sample_count?: number;
  light_daytime_sample_count?: number;
  light_daytime_window_label?: string;
  distance?: number;
  state_level?: string;
  rag?: string;
  alerts?: string[];
}

export interface SensorLatest {
  latest_realtime: SensorReading | null;
  latest_hourly: SensorReading | null;
  latest_merged: SensorReading | null;
  latest_state?: {
    level?: string;
    rag?: string;
    alerts?: string[];
    details?: Record<string, unknown>;
  } | null;
  sensor_semantics?: Record<string, unknown>;
  sensor_summary?: string | null;
  runtime_settings?: RuntimeSettings;
  distance_inside_threshold?: boolean;
  wake_eligible?: boolean;
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

export async function listSessions(limit = 5, kind: 'chat' | 'voice' = 'chat'): Promise<SessionSummary[]> {
  const params = new URLSearchParams({
    limit: String(limit),
    kind,
  });
  const data = await fetchJson<{ sessions: SessionSummary[] }>(`${API}/sessions?${params.toString()}`);
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

export async function askChat(
  text: string,
  sessionId?: string,
  isTest?: boolean,
  voiceName?: string,
  personaMemo?: string,
): Promise<AskResult> {
  return fetchJson<AskResult>(`${API}/ask`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      question: text,
      session_id: sessionId ?? null,
      session_kind: 'chat',
      use_sensor_context: true,
      is_test: isTest ?? null,
      voice_name: voiceName ?? getStoredVoiceName(),
      persona_memo: personaMemo ?? getStoredPersonaMemo(),
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
      persona_memo: options?.personaMemo ?? getStoredPersonaMemo(),
      system_memo: options?.systemMemo ?? null,
      voice_name: options?.voiceName ?? getStoredVoiceName(),
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
