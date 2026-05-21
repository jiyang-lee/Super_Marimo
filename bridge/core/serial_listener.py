import collections
import io
import time
import wave
from pathlib import Path
from typing import Any, Callable

from bridge.core.vad_profile import build_vad_profile

SAMPLE_RATE = 16_000
CHANNELS = 1
SAMPLE_WIDTH = 2
FRAME_SAMPLES = 256
FRAME_BYTES = FRAME_SAMPLES * SAMPLE_WIDTH


def compute_rms(frame: bytes) -> float:
    if not frame:
        return 0.0
    sample_count = len(frame) // 2
    if sample_count == 0:
        return 0.0

    total = 0.0
    for index in range(0, sample_count * 2, 2):
        sample = int.from_bytes(frame[index : index + 2], byteorder="little", signed=True)
        total += float(sample * sample)
    return (total / sample_count) ** 0.5


def open_serial(port: str, baudrate: int):
    import serial

    return serial.Serial(port=port, baudrate=baudrate, timeout=0.25)


def wav_bytes_from_pcm(pcm_bytes: bytes) -> bytes:
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wav_file:
        wav_file.setnchannels(CHANNELS)
        wav_file.setsampwidth(SAMPLE_WIDTH)
        wav_file.setframerate(SAMPLE_RATE)
        wav_file.writeframes(pcm_bytes)
    return buffer.getvalue()


def prune_debug_wavs(debug_dir: Path, prefix: str, retain_count: int) -> None:
    if retain_count < 0 or not debug_dir.exists():
        return

    wav_files = sorted(
        debug_dir.glob(f"{prefix}-*.wav"),
        key=lambda path: path.stat().st_mtime,
    )
    excess = len(wav_files) - retain_count
    if excess <= 0:
        return

    for wav_path in wav_files[:excess]:
        try:
            wav_path.unlink()
        except OSError:
            pass


def save_debug_wav(debug_dir: Path, prefix: str, pcm_bytes: bytes, retain_count: int = 25) -> Path:
    debug_dir.mkdir(parents=True, exist_ok=True)
    target = debug_dir / f"{prefix}-{time.time_ns()}.wav"
    target.write_bytes(wav_bytes_from_pcm(pcm_bytes))
    prune_debug_wavs(debug_dir, prefix, retain_count)
    return target


class SerialListener:
    def __init__(self, args: Any):
        self.args = args
        self.debug_dir = Path(args.debug_dir)
        self.debug_retain_count = int(getattr(args, "debug_retain_count", 25))
        self.serial_port = open_serial(args.port, args.baudrate)

    def run(
        self,
        on_segment: Callable[[bytes], None],
        on_speech_started: Callable[[float], None] = None,
        on_speech_ended: Callable[[int, int, int], None] = None,
        is_boosted: Callable[[], bool] | None = None,
    ) -> None:
        pre_roll = collections.deque(maxlen=self.args.pre_roll_frames)
        active_frames: list[bytes] = []
        active = False
        start_hits = 0
        silence_hits = 0
        max_active_frames = int((self.args.max_segment_sec * SAMPLE_RATE) / FRAME_SAMPLES)

        print(f"[serial] listening on {self.args.port} @ {self.args.baudrate}")

        try:
            while True:
                frame = self.serial_port.read(FRAME_BYTES)
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
            self.serial_port.close()
