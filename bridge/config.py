import argparse
import os


DEFAULT_PERSONA_MEMO = (
    "짧고 자연스럽게 답한다. "
    "보통 1~2문장, 길어도 3문장을 넘기지 않는다."
)

DEFAULT_SYSTEM_MEMO = (
    "호출어 직후에는 친절한 인사만 하고, "
    "답변은 한국어로만 짧고 자연스럽게 말해준다."
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Marimo Voice Bridge (Windows Host)")
    parser.add_argument("--port", default="COM4", help="Serial port, e.g. COM4")
    parser.add_argument("--baudrate", type=int, default=921600, help="Serial baudrate")
    parser.add_argument(
        "--source",
        default="serial",
        choices=["serial", "mic"],
        help="Audio source: serial (RP2040 mic) or mic (local PC/notebook mic)",
    )
    # Windows Host 주소 기준 (Bridge는 Docker 외부에서 실행됨)
    parser.add_argument("--stt-endpoint", default="http://127.0.0.1:8002/stt")
    parser.add_argument("--stt-model", default="fast", choices=["fast", "accurate"])
    parser.add_argument("--voice-agent-url", default="http://127.0.0.1:8003")
    parser.add_argument("--api-server-url", default="http://127.0.0.1:8000")
    parser.add_argument("--events-endpoint", default="http://127.0.0.1:8000/events")
    parser.add_argument("--shared-audio-dir", default="shared\\audio")
    parser.add_argument("--session-state-file", default="bridge\\session.json")
    parser.add_argument("--history-turns", type=int, default=6)
    parser.add_argument("--wake-timeout-sec", type=int, default=45)
    parser.add_argument("--start-rms", type=int, default=900)
    parser.add_argument("--stop-rms", type=int, default=500)
    parser.add_argument("--start-frames", type=int, default=2)
    parser.add_argument("--silence-frames", type=int, default=8)
    parser.add_argument("--max-segment-sec", type=float, default=8.0)
    parser.add_argument("--min-segment-sec", type=float, default=0.3)
    parser.add_argument(
        "--wake-min-segment-sec",
        type=float,
        default=0.3,
        help="Minimum segment length when the bridge is idle and waiting for wakeword",
    )
    parser.add_argument("--pre-roll-frames", type=int, default=8)
    parser.add_argument("--debug-dir", default="bridge\\captures")
    parser.add_argument(
        "--debug-retain-count",
        type=int,
        default=25,
        help="Max number of debug WAV files to keep per prefix",
    )
    parser.add_argument("--poll-interval-ms", type=int, default=200, help="Audio player polling interval")
    parser.add_argument(
        "--distance-followup-timeout-sec",
        type=int,
        default=30,
        help="Seconds to keep conversation open after proactive greeting playback",
    )
    parser.add_argument(
        "--reply-boost-sec",
        type=int,
        default=15,
        help="Seconds to keep a short boosted listen window after assistant speech",
    )
    parser.add_argument(
        "--tts-preplay-guard-sec",
        type=float,
        default=0.5,
        help="Seconds to mute STT immediately after an answer is requested, before playback starts",
    )
    parser.add_argument(
        "--reply-min-segment-sec",
        type=float,
        default=0.35,
        help="Minimum segment length during the boosted reply window",
    )
    parser.add_argument(
        "--reply-start-rms",
        type=int,
        default=650,
        help="Lower start RMS threshold during the boosted reply window",
    )
    parser.add_argument(
        "--reply-stop-rms",
        type=int,
        default=325,
        help="Lower stop RMS threshold during the boosted reply window",
    )
    parser.add_argument(
        "--reply-start-frames",
        type=int,
        default=1,
        help="Start frames required during the boosted reply window",
    )
    parser.add_argument(
        "--reply-silence-frames",
        type=int,
        default=14,
        help="Silence frames required during the boosted reply window",
    )
    return parser
