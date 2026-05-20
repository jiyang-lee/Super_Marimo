import os
from datetime import timedelta, timezone


LLM_SERVER_URL = os.getenv("LLM_SERVER_URL", "http://llm-server:8000")
DATABASE_URL = os.getenv("DATABASE_URL", "")
DB_TIMEZONE = "Asia/Seoul"
KST = timezone(timedelta(hours=9), name="KST")
REALTIME_RETENTION_DAYS = 7
REALTIME_CLEANUP_INTERVAL_SECONDS = 7 * 24 * 60 * 60

EVENT_RETENTION_DAYS = {
    "realtime_sensor": 7,
    "speech_started": 1,
    "speech_ended": 1,
    "interaction_log": 365,
    "proactive_greeting": 30,
    "manual_test": 7,
    "runtime_settings_history": 365,
}
EVENT_CLEANUP_INTERVAL_SECONDS = int(os.getenv("EVENT_CLEANUP_INTERVAL_SECONDS", "3600"))
SESSION_HISTORY_LIMIT = 16
SENSOR_WARNING_DISTANCE_THRESHOLD_CM = float(os.getenv("SENSOR_WARNING_DISTANCE_THRESHOLD_CM", "50"))
SENSOR_WARNING_COOLDOWN_SECONDS = int(os.getenv("SENSOR_WARNING_COOLDOWN_SECONDS", "5"))
PROACTIVE_GREETING_COOLDOWN_SECONDS = int(os.getenv("PROACTIVE_GREETING_COOLDOWN_SECONDS", "60"))
PROACTIVE_GREETING_TEXT = os.getenv(
    "PROACTIVE_GREETING_TEXT",
    "안녕하세요. 마리모가 먼저 인사드릴게요.",
)
PROACTIVE_GREETING_USE_LLM = os.getenv("PROACTIVE_GREETING_USE_LLM", "false").lower() == "true"
PROACTIVE_GREETING_LLM_PROMPT = os.getenv(
    "PROACTIVE_GREETING_LLM_PROMPT",
    "사람이 가까이 왔어. 한국어로 짧고 친근하게 인사해. 1문장.",
)
DEVICE_EVENT_TYPES = (
    "wakeword",
    "speech_started",
    "speech_ended",
    "stt_completed",
    "llm_completed",
    "tts_played",
    "sensor_warning",
    "proactive_greeting",
    "manual_test",
)
LIGHT_RAW_SAMPLE_INTERVAL_SECONDS = int(os.getenv("LIGHT_RAW_SAMPLE_INTERVAL_SECONDS", "10"))
