-- One-shot migration script to add runtime_settings_history table
-- for existing databases already running in production or manual environments.
-- Run this manually via psql or your DB admin tool.
-- New Docker/dev environments will auto-create this table via init_db().

CREATE TABLE IF NOT EXISTS runtime_settings_history (
    history_id BIGSERIAL PRIMARY KEY,
    setting_key TEXT NOT NULL,
    previous_value JSONB,
    new_value JSONB NOT NULL,
    changed_by TEXT,
    changed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    action_type TEXT,
    summary TEXT
);

CREATE INDEX IF NOT EXISTS idx_runtime_settings_history_key_created_at
ON runtime_settings_history (setting_key, changed_at DESC);
