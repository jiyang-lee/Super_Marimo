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
    # Windows Host 주소 기준 (Bridge는 Docker 외부에서 실행됨)
    parser.add_argument("--stt-endpoint", default="http://127.0.0.1:8002/stt")
    parser.add_argument("--stt-model", default="fast", choices=["fast", "accurate"])
    parser.add_argument("--voice-agent-url", default="http://127.0.0.1:8003")
    parser.add_argument("--api-server-url", default="http://127.0.0.1:8000")
    parser.add_argument("--events-endpoint", default="http://127.0.0.1:8000/events")
    parser.add_argument("--shared-audio-dir", default="shared\\audio")
    parser.add_argument("--session-state-file", default="bridge\\session.json")
    parser.add_argument("--history-turns", type=int, default=6)
    parser.add_argument("--wake-timeout-sec", type=int, default=120)
    parser.add_argument("--start-rms", type=int, default=900)
    parser.add_argument("--stop-rms", type=int, default=500)
    parser.add_argument("--start-frames", type=int, default=2)
    parser.add_argument("--silence-frames", type=int, default=10)
    parser.add_argument("--max-segment-sec", type=float, default=8.0)
    parser.add_argument("--min-segment-sec", type=float, default=0.7)
    parser.add_argument("--pre-roll-frames", type=int, default=8)
    parser.add_argument("--debug-dir", default="bridge\\captures")
    parser.add_argument(
        "--debug-retain-count",
        type=int,
        default=25,
        help="Max number of debug WAV files to keep per prefix",
    )
    parser.add_argument("--poll-interval-ms", type=int, default=200, help="Audio player polling interval")
    parser.add_argument("--distance-followup-timeout-sec", type=int, default=30, help="Seconds to keep conversation open after proactive greeting playback")
    return parser
