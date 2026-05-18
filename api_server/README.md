# API Server

`api-server` is the persistence and policy layer for the beta stack.

## Responsibilities
- session storage
- session message storage
- interaction log storage
- device event log storage
- sensor ingest and state judgment
- downstream LLM orchestration

## Main APIs
- `GET /health`
- `POST /ask`
- `POST /voice/ask`
- `POST /events/wakeword`
- `POST /events/manual-test`
- `POST /sensor/status`
- `POST /sensor/realtime-ingest`
- `POST /sensor/hourly-ingest`
- `GET /sessions`
- `GET /sessions/{session_id}`

## Notes
- `device_event_log` stores wakeword and manual test events for now.
- `sensor-warning` is deferred until threshold policy is defined by the user.
- `interaction_log` stays separate from device events.
- The service initializes the DB schema on startup.
