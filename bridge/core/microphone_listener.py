import collections
import time
from pathlib import Path
from typing import Any, Callable

from bridge.core.serial_listener import (
    FRAME_BYTES,
    FRAME_SAMPLES,
    SAMPLE_RATE,
    SAMPLE_WIDTH,
    compute_rms,
    save_debug_wav,
)
from bridge.core.vad_profile import build_vad_profile


class MicrophoneListener:
    def __init__(self, args: Any):
        self.args = args
        self.debug_dir = Path(args.debug_dir)
        self.debug_retain_count = int(getattr(args, "debug_retain_count", 25))

    def run(
        self,
        on_segment: Callable[[bytes], None],
        on_speech_started: Callable[[float], None] = None,
        on_speech_ended: Callable[[int, int, int], None] = None,
        is_boosted: Callable[[], bool] | None = None,
    ) -> None:
        import pyaudio

        audio = pyaudio.PyAudio()
        stream = audio.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=SAMPLE_RATE,
            input=True,
            frames_per_buffer=FRAME_SAMPLES,
        )

        pre_roll = collections.deque(maxlen=self.args.pre_roll_frames)
        active_frames: list[bytes] = []
        active = False
        start_hits = 0
        silence_hits = 0
        max_active_frames = int((self.args.max_segment_sec * SAMPLE_RATE) / FRAME_SAMPLES)

        print("[mic] listening on default microphone")

        try:
            while True:
                frame = stream.read(FRAME_SAMPLES, exception_on_overflow=False)
                if len(frame) != FRAME_BYTES:
                    continue

                rms = compute_rms(frame)
                vad = build_vad_profile(self.args, boosted=bool(is_boosted and is_boosted()))

                if not active:
                    pre_roll.append(frame)
                    if rms >= vad.start_rms:
                        start_hits += 1
                    else:
                        start_hits = 0

                    if start_hits >= vad.start_frames:
                        active = True
                        active_frames = list(pre_roll)
                        silence_hits = 0
                        start_hits = 0
                        if on_speech_started:
                            on_speech_started(rms)
                    continue

                active_frames.append(frame)
                if rms <= vad.stop_rms:
                    silence_hits += 1
                else:
                    silence_hits = 0

                if silence_hits >= vad.silence_frames or len(active_frames) >= max_active_frames:
                    if on_speech_ended:
                        on_speech_ended(len(active_frames), silence_hits, max_active_frames)
                    pcm = b"".join(active_frames)
                    save_debug_wav(self.debug_dir, "segment", pcm, retain_count=self.debug_retain_count)
                    on_segment(pcm)
                    active = False
                    active_frames = []
                    silence_hits = 0
                    pre_roll.clear()
        finally:
            stream.stop_stream()
            stream.close()
            audio.terminate()
