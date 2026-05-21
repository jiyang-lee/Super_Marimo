from bridge.core.audio_player import AudioPlayer
from pathlib import Path


def test_extract_event_id_with_timestamp_suffix() -> None:
    player = AudioPlayer("shared/audio")

    assert player._extract_event_id("event_proactive_greeting_3227_390.wav") == 3227


def test_event_audio_allowlist() -> None:
    player = AudioPlayer("shared/audio")

    assert player._should_play_file("event_proactive_greeting_3227_390.wav")
    assert not player._should_play_file("event_stt_completed_3228_400.wav")
    assert player._should_play_file("ask_abc.wav")


def test_get_wav_duration_sec(tmp_path) -> None:
    import wave

    wav_path = Path(tmp_path) / "sample.wav"
    with wave.open(str(wav_path), "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(16000)
        wav_file.writeframes(b"\x00\x00" * 1600)

    player = AudioPlayer(str(tmp_path))
    duration = player._get_wav_duration_sec(wav_path)

    assert 0.09 < duration < 0.11
