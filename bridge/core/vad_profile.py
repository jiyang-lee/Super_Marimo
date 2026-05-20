from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class VadProfile:
    start_rms: int
    stop_rms: int
    start_frames: int
    silence_frames: int
    min_segment_sec: float


def build_vad_profile(args: Any, boosted: bool = False) -> VadProfile:
    if not boosted:
        return VadProfile(
            start_rms=int(args.start_rms),
            stop_rms=int(args.stop_rms),
            start_frames=int(args.start_frames),
            silence_frames=int(args.silence_frames),
            min_segment_sec=float(args.min_segment_sec),
        )

    start_rms = int(getattr(args, "reply_start_rms", max(300, int(args.start_rms * 0.75))))
    stop_rms = int(getattr(args, "reply_stop_rms", max(200, int(args.stop_rms * 0.7))))
    start_frames = int(getattr(args, "reply_start_frames", 1))
    silence_frames = int(getattr(args, "reply_silence_frames", max(8, int(args.silence_frames * 1.25))))
    min_segment_sec = float(getattr(args, "reply_min_segment_sec", max(0.35, min(float(args.min_segment_sec), 0.5))))

    return VadProfile(
        start_rms=start_rms,
        stop_rms=stop_rms,
        start_frames=start_frames,
        silence_frames=silence_frames,
        min_segment_sec=min_segment_sec,
    )
