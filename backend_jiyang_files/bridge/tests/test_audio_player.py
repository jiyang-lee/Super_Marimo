from bridge.core.audio_player import AudioPlayer


def test_extract_event_id_with_timestamp_suffix() -> None:
    player = AudioPlayer("shared/audio")

    assert player._extract_event_id("event_proactive_greeting_3227_390.wav") == 3227


def test_event_audio_allowlist() -> None:
    player = AudioPlayer("shared/audio")

    assert player._should_play_file("event_proactive_greeting_3227_390.wav")
    assert not player._should_play_file("event_stt_completed_3228_400.wav")
    assert player._should_play_file("ask_abc.wav")
