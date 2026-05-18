import os
import time
from pathlib import Path

import winsound


class AudioPlayer:
    def __init__(self, shared_audio_dir: str, poll_interval_ms: int = 200):
        self.audio_dir = Path(shared_audio_dir)
        self.poll_interval_ms = poll_interval_ms
        self._played: set[str] = set()

    def start(self) -> None:
        print(f"[audio_player] watching {self.audio_dir}")
        while True:
            self._poll_once()
            time.sleep(self.poll_interval_ms / 1000.0)

    def _poll_once(self) -> None:
        if not self.audio_dir.exists():
            return

        wav_files = sorted(self.audio_dir.glob("*.wav"), key=lambda p: p.stat().st_mtime)
        for wav_path in wav_files:
            name = wav_path.name
            if name in self._played:
                try:
                    wav_path.unlink()
                except OSError:
                    pass
                self._played.discard(name)
                continue

            print(f"[audio_player] playing {name}")
            try:
                winsound.PlaySound(str(wav_path), winsound.SND_FILENAME)
                print(f"[audio_player] finished {name}")
            except Exception as exc:
                print(f"[audio_player] playback error: {exc}")
            finally:
                self._played.add(name)
                try:
                    wav_path.unlink()
                except OSError:
                    pass
                self._played.discard(name)
