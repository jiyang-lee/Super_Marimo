from core.event_poller import EventPoller


class _FakeApiClient:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []
        self.marked = []

    def list_events(self, **kwargs):
        self.calls.append(kwargs)
        if self.responses:
            return self.responses.pop(0)
        return {"events": []}

    def mark_event_played(self, event_id):
        self.marked.append(event_id)
        return {"event_id": event_id, "played": True}


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
                }
            ]
        },
        {
            "events": [
                {
                    "event_id": 22,
                    "event_type": "proactive_greeting",
                    "generated_text": "second greeting",
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
    assert api_client.calls[0]["order"] == "asc"
    assert api_client.marked == [21, 22]
    assert tts_client.calls == [
        ("first alert", "event_sensor_warning_21"),
        ("second greeting", "event_proactive_greeting_22"),
    ]
