from core.event_poller import EventPoller


class _FakeApiClient:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []
        self.marked = []
        self.status_updates = []

    def list_events(self, **kwargs):
        self.calls.append(kwargs)
        if self.responses:
            return self.responses.pop(0)
        return {"events": []}

    def mark_event_played(self, event_id):
        self.marked.append(event_id)
        return {"event_id": event_id, "played": True}

    def update_event_status(self, event_id, status):
        self.status_updates.append((event_id, status))
        return {"event_id": event_id, "status": status}


class _FakeTtsClient:
    def __init__(self):
        self.calls = []

    def synthesize_to_file(self, text, prefix="tts"):
        self.calls.append((text, prefix))
        return f"{prefix}.wav"


def test_event_poller_consumes_oldest_pending_events_first() -> None:
    responses = [
        {
            "events": [
                {
                    "event_id": 21,
                    "event_type": "sensor_warning",
                    "generated_text": "first alert",
                    "status": "pending",
                }
            ]
        },
        {
            "events": [
                {
                    "event_id": 22,
                    "event_type": "proactive_greeting",
                    "generated_text": "second greeting",
                    "status": "pending",
                }
            ]
        },
        {"events": []},
    ]
    api_client = _FakeApiClient(responses)
    tts_client = _FakeTtsClient()
    poller = EventPoller(
        api_client,
        tts_client,
        event_types=["proactive_greeting", "sensor_warning"],
    )

    poller._poll_once()

    assert api_client.calls[0]["event_types"] == ["proactive_greeting", "sensor_warning"]
    assert api_client.calls[0]["status"] == "pending"
    assert api_client.calls[0]["order"] == "asc"
    assert api_client.status_updates == [
        (21, "processing"),
        (21, "tts_generated"),
        (22, "processing"),
        (22, "tts_generated"),
    ]
    assert tts_client.calls == [
        ("first alert", "event_sensor_warning_21"),
        ("second greeting", "event_proactive_greeting_22"),
    ]


def test_event_poller_rejects_unexpected_event_type() -> None:
    responses = [
        {
            "events": [
                {
                    "event_id": 31,
                    "event_type": "stt_completed",
                    "generated_text": "do not synthesize",
                    "status": "pending",
                }
            ]
        },
        {"events": []},
    ]
    api_client = _FakeApiClient(responses)
    tts_client = _FakeTtsClient()
    poller = EventPoller(api_client, tts_client, event_types=["proactive_greeting"])

    poller._poll_once()

    assert api_client.status_updates == [(31, "failed")]
    assert tts_client.calls == []
