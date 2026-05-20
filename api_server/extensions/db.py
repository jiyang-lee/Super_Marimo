from datetime import datetime
from typing import Optional

import psycopg
import threading
from fastapi import HTTPException
from psycopg.rows import dict_row

from config import (
    DATABASE_URL,
    DB_TIMEZONE,
    DEVICE_EVENT_TYPES,
    REALTIME_CLEANUP_INTERVAL_SECONDS,
    REALTIME_RETENTION_DAYS,
)
from utils import now_kst

last_realtime_cleanup_at: Optional[datetime] = None


def get_db_connection():
    if not DATABASE_URL:
        raise HTTPException(status_code=503, detail="DATABASE_URL is not configured")
    return psycopg.connect(
        DATABASE_URL,
        row_factory=dict_row,
        options=f"-c timezone={DB_TIMEZONE}",
    )


def init_db() -> None:
    if not DATABASE_URL:
        return

    allowed_event_types_sql = ", ".join(f"'{event_type}'" for event_type in DEVICE_EVENT_TYPES)
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS session (
                    session_id UUID PRIMARY KEY,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    last_seen_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    ended_at TIMESTAMPTZ NULL,
                    turn_count INTEGER NOT NULL DEFAULT 0,
                    meta JSONB NOT NULL DEFAULT '{}'::jsonb
                )
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS session_message (
                    message_id BIGSERIAL PRIMARY KEY,
                    session_id UUID NOT NULL REFERENCES session(session_id) ON DELETE CASCADE,
                    role TEXT NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
                    content TEXT NOT NULL,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    meta JSONB NOT NULL DEFAULT '{}'::jsonb
                )
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS sensor_readings (
                    reading_id BIGSERIAL PRIMARY KEY,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    sensor_type TEXT NOT NULL CHECK (sensor_type IN ('realtime', 'hourly')),
                    payload JSONB NOT NULL,
                    state_level TEXT NOT NULL CHECK (state_level IN ('normal', 'warning', 'danger')),
                    state_alerts JSONB NOT NULL DEFAULT '[]'::jsonb
                )
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS water_raw_samples (
                    sample_id BIGSERIAL PRIMARY KEY,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    raw_value INTEGER NOT NULL
                )
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS light_raw_samples (
                    sample_id BIGSERIAL PRIMARY KEY,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    raw_value INTEGER NOT NULL
                )
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS runtime_settings (
                    setting_key TEXT PRIMARY KEY,
                    setting_value JSONB NOT NULL,
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS interaction_log (
                    interaction_id BIGSERIAL PRIMARY KEY,
                    session_id UUID NOT NULL REFERENCES session(session_id) ON DELETE CASCADE,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    stt_text TEXT NOT NULL,
                    llm_answer TEXT NOT NULL,
                    tts_text TEXT NOT NULL,
                    sensor_json JSONB NOT NULL DEFAULT '{}'::jsonb,
                    state_level TEXT NOT NULL CHECK (state_level IN ('normal', 'warning', 'danger', 'chat')),
                    state_alerts JSONB NOT NULL DEFAULT '[]'::jsonb,
                    meta JSONB NOT NULL DEFAULT '{}'::jsonb
                )
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS device_event_log (
                    event_id BIGSERIAL PRIMARY KEY,
                    session_id UUID NULL REFERENCES session(session_id) ON DELETE SET NULL,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    event_type TEXT NOT NULL,
                    device_id TEXT NOT NULL DEFAULT '',
                    trigger_source TEXT NOT NULL DEFAULT 'manual',
                    distance DOUBLE PRECISION NULL,
                    sensor_json JSONB NOT NULL DEFAULT '{}'::jsonb,
                    state_level TEXT NOT NULL CHECK (state_level IN ('normal', 'warning', 'danger', 'chat')),
                    state_alerts JSONB NOT NULL DEFAULT '[]'::jsonb,
                    generated_text TEXT NOT NULL DEFAULT '',
                    played BOOLEAN NOT NULL DEFAULT FALSE,
                    meta JSONB NOT NULL DEFAULT '{}'::jsonb
                )
                """
            )
            cur.execute(
                """
                ALTER TABLE device_event_log
                DROP CONSTRAINT IF EXISTS device_event_log_event_type_check
                """
            )
            cur.execute(
                """
                ALTER TABLE device_event_log
                ADD CONSTRAINT device_event_log_event_type_check
                CHECK (event_type IN ({allowed_event_types_sql}))
                """.format(allowed_event_types_sql=allowed_event_types_sql)
            )
            cur.execute(
                "CREATE INDEX IF NOT EXISTS idx_session_last_seen_at ON session (last_seen_at DESC)"
            )
            cur.execute(
                "CREATE INDEX IF NOT EXISTS idx_session_message_session_created_at ON session_message (session_id, created_at DESC)"
            )
            cur.execute(
                "CREATE INDEX IF NOT EXISTS idx_sensor_readings_type_created_at ON sensor_readings (sensor_type, created_at DESC)"
            )
            cur.execute(
                "CREATE INDEX IF NOT EXISTS idx_water_raw_samples_created_at ON water_raw_samples (created_at DESC)"
            )
            cur.execute(
                "CREATE INDEX IF NOT EXISTS idx_light_raw_samples_created_at ON light_raw_samples (created_at DESC)"
            )
            cur.execute(
                "CREATE INDEX IF NOT EXISTS idx_interaction_log_session_created_at ON interaction_log (session_id, created_at DESC)"
            )
            cur.execute(
                "CREATE INDEX IF NOT EXISTS idx_device_event_log_type_created_at ON device_event_log (event_type, created_at DESC)"
            )
            cur.execute(
                "CREATE INDEX IF NOT EXISTS idx_device_event_log_played_type_created_at ON device_event_log (played, event_type, created_at DESC)"
            )
            cur.execute(
                "CREATE INDEX IF NOT EXISTS idx_device_event_log_session_created_at ON device_event_log (session_id, created_at DESC)"
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS runtime_settings_history (
                    history_id BIGSERIAL PRIMARY KEY,
                    setting_key TEXT NOT NULL,
                    previous_value JSONB,
                    new_value JSONB NOT NULL,
                    changed_by TEXT,
                    changed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    action_type TEXT,
                    summary TEXT
                )
                """
            )
            cur.execute(
                "CREATE INDEX IF NOT EXISTS idx_runtime_settings_history_key_created_at ON runtime_settings_history (setting_key, changed_at DESC)"
            )
            cur.execute(
                """
                ALTER TABLE device_event_log
                ADD COLUMN IF NOT EXISTS status VARCHAR(20) NOT NULL DEFAULT 'pending'
                """
            )
            cur.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_device_event_log_status
                ON device_event_log (status, created_at DESC)
                """
            )
        conn.commit()


def cleanup_old_realtime_rows(force: bool = False) -> int:
    global last_realtime_cleanup_at

    now = now_kst()
    if (
        not force
        and last_realtime_cleanup_at is not None
        and (now - last_realtime_cleanup_at).total_seconds() < REALTIME_CLEANUP_INTERVAL_SECONDS
    ):
        return 0

    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                DELETE FROM sensor_readings
                WHERE sensor_type = 'realtime'
                  AND created_at < NOW() - (%s * INTERVAL '1 day')
                RETURNING reading_id
                """,
                (REALTIME_RETENTION_DAYS,),
            )
            deleted_count = cur.rowcount
        conn.commit()

    last_realtime_cleanup_at = now
    return deleted_count


def cleanup_expired_events(force: bool = False) -> dict[str, int]:
    from config import EVENT_RETENTION_DAYS

    results: dict[str, int] = {}
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            # speech_started / speech_ended
            for event_type in ("speech_started", "speech_ended"):
                days = EVENT_RETENTION_DAYS.get(event_type, 1)
                cur.execute(
                    """
                    DELETE FROM device_event_log
                    WHERE event_type = %s
                      AND created_at < NOW() - (%s * INTERVAL '1 day')
                    """,
                    (event_type, days),
                )
                results[event_type] = cur.rowcount

            # proactive_greeting
            days = EVENT_RETENTION_DAYS.get("proactive_greeting", 30)
            cur.execute(
                """
                DELETE FROM device_event_log
                WHERE event_type = 'proactive_greeting'
                  AND created_at < NOW() - (%s * INTERVAL '1 day')
                """,
                (days,),
            )
            results["proactive_greeting"] = cur.rowcount

            # manual_test
            days = EVENT_RETENTION_DAYS.get("manual_test", 7)
            cur.execute(
                """
                DELETE FROM device_event_log
                WHERE event_type = 'manual_test'
                  AND created_at < NOW() - (%s * INTERVAL '1 day')
                """,
                (days,),
            )
            results["manual_test"] = cur.rowcount

            # runtime_settings_history
            history_days = EVENT_RETENTION_DAYS.get("runtime_settings_history", 365)
            cur.execute(
                """
                DELETE FROM runtime_settings_history
                WHERE changed_at < NOW() - (%s * INTERVAL '1 day')
                """,
                (history_days,),
            )
            results["runtime_settings_history"] = cur.rowcount

        conn.commit()
    return results


_cleanup_timer: Optional[threading.Timer] = None


def start_cleanup_timer(interval_sec: int = 3600) -> None:
    global _cleanup_timer

    def _run() -> None:
        try:
            cleanup_old_realtime_rows(force=True)
            cleanup_expired_events(force=True)
        except Exception:
            import logging
            logging.getLogger("db_cleanup").exception("Periodic cleanup failed")
        finally:
            start_cleanup_timer(interval_sec)

    if _cleanup_timer is not None:
        _cleanup_timer.cancel()
    _cleanup_timer = threading.Timer(interval_sec, _run)
    _cleanup_timer.daemon = True
    _cleanup_timer.start()
