import re
import wave
import time
from pathlib import Path
from typing import Any, Callable, Optional

import winsound


class AudioPlayer:
    def __init__(
        self,
        shared_audio_dir: str,
        poll_interval_ms: int = 200,
        api_bridge: Any = None,
        on_playing: Callable[[str], None] | None = None,
        on_played: Callable[[str], None] | None = None,
        should_suppress_proactive: Callable[[], bool] | None = None,
    ):
        self.audio_dir = Path(shared_audio_dir)
        self.poll_interval_ms = poll_interval_ms
        self._played: set[str] = set()
        self.api_bridge = api_bridge
        self.on_playing = on_playing
        self.on_played = on_played
        self.should_suppress_proactive = should_suppress_proactive

    def _extract_event_id(self, name: str) -> Optional[int]:
        if not name.startswith("event_") or not name.endswith(".wav"):
            return None
        core = name[6:-4]
        m = re.search(r"_(\d+)(?:_\d+)?$", core)
        if m:
            return int(m.group(1))
        return None

    def _should_play_file(self, name: str) -> bool:
        if name.startswith("ask_") or name.startswith("speak_"):
            return True
        if name.startswith("event_proactive_greeting_"):
            return self._extract_event_id(name) is not None
        if name.startswith("event_"):
            return False
        return True

    def _update_status(self, event_id: Optional[int], status: str) -> None:
        if event_id is None or self.api_bridge is None:
            return
        try:
            self.api_bridge.update_event_status(event_id, status)
        except Exception as exc:
            print(f"[audio_player] status update failed: {exc}")

    def start(self) -> None:
        print(f"[audio_player] watching {self.audio_dir}")
        while True:
            self._poll_once()
            time.sleep(self.poll_interval_ms / 1000.0)

    def _get_wav_duration_sec(self, wav_path: Path) -> float:
        try:
            with wave.open(str(wav_path), "rb") as wav_file:
                frame_count = wav_file.getnframes()
                frame_rate = wav_file.getframerate() or 1
                return float(frame_count) / float(frame_rate)
        except Exception:
            return 0.0

    def _poll_once(self) -> None:
        if not self.audio_dir.exists():
            return

        wav_files = sorted(self.audio_dir.glob("*.wav"), key=lambda p: p.stat().st_mtime)
        for wav_path in wav_files:
            name = wav_path.name
            if not self._should_play_file(name):
                event_id = self._extract_event_id(name)
                print(f"[audio_player] deleting unsupported event audio {name}")
                self._update_status(event_id, "failed")
                try:
                    wav_path.unlink()
                except OSError:
                    pass
                continue

            # Proactive greeting is the only event-driven audio that should be spoken.
            if name.startswith("event_proactive_greeting_") and self.should_suppress_proactive is not None:
                if self.should_suppress_proactive():
                    event_id = self._extract_event_id(name)
                    print(f"[audio_player] suppressing proactive greeting {name} because conversation is active")
                    self._update_status(event_id, "failed")
                    try:
                        wav_path.unlink()
                    except OSError:
                        pass
                    continue

            if name in self._played:
                try:
                    wav_path.unlink()
                except OSError:
                    pass
                self._played.discard(name)
                continue

            event_id = self._extract_event_id(name)
            print(f"[audio_player] playing {name}")
            self._update_status(event_id, "playing")
            try:
                duration_sec = self._get_wav_duration_sec(wav_path)
                if self.on_playing is not None:
                    try:
                        self.on_playing(name, duration_sec)
                    except Exception as exc:
                        print(f"[audio_player] on_playing callback error: {exc}")
                winsound.PlaySound(str(wav_path), winsound.SND_FILENAME)
                print(f"[audio_player] finished {name}")
                self._update_status(event_id, "played")
                if (
                    (name.startswith("event_proactive_greeting_") or name.startswith("ask_") or name.startswith("speak_"))
                    and self.on_played is not None
                ):
                    try:
                        self.on_played(name)
                    except Exception as exc:
                        print(f"[audio_player] on_played callback error: {exc}")
            except Exception as exc:
                print(f"[audio_player] playback error: {exc}")
                self._update_status(event_id, "failed")
            finally:
                self._played.add(name)
                try:
                    wav_path.unlink()
                except OSError:
                    pass
                self._played.discard(name)
