from __future__ import annotations

import argparse
import collections
import io
import json
import mimetypes
import os
import random
import re
import tempfile
import time
import uuid
import threading
import wave
import unicodedata
from pathlib import Path
from urllib import error as urlerror
from urllib import request as urlrequest
from urllib.parse import urlsplit, urlunsplit

import winsound


SAMPLE_RATE = 16_000
CHANNELS = 1
SAMPLE_WIDTH = 2
FRAME_SAMPLES = 256
FRAME_BYTES = FRAME_SAMPLES * SAMPLE_WIDTH

WAKE_PREFIXES = (
    "안녕마리모",
    "안녕하세요마리모",
    "마리모",
    "마니모",
    "마린모",
    "마리모야",
    "마리모씨",
    "마니모야",
    "마린모야",
)

WAKE_SUFFIXES = (
    "",
    "야",
    "씨",
    "님",
    "요",
    "좀",
    "부탁",
    "불러",
    "불러줘",
    "도와줘",
    "도와줄래",
    "말해줘",
)

EXIT_PHRASES = (
    "잘가",
    "잘 가",
    "바이",
    "그만해",
    "대화 종료",
    "대화종료",
    "종료해 마리모",
    "종료해마리모",
)

WAKE_GREETINGS = (
    "안녕, 불렀구나. 천천히 말해줘.",
    "응, 마리모야. 편하게 이야기해도 돼.",
    "안녕. 무엇을 도와줄까?",
    "그래, 듣고 있어. 말해줘.",
)

DEFAULT_PERSONA_MEMO = (
    "짧고 자연스럽게 답한다. "
    "보통 1~2문장, 길어도 3문장을 넘기지 않는다."
)

DEFAULT_SYSTEM_MEMO = (
    "호출어 직후에는 친절한 인사만 하고, "
    "답변은 한국어로만 짧고 자연스럽게 말해준다."
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="RP2040 serial voice prototype")
    parser.add_argument("--port", default="COM4", help="Serial port, e.g. COM4")
    parser.add_argument("--baudrate", type=int, default=921600, help="Serial baudrate")
    parser.add_argument("--stt-endpoint", default="http://127.0.0.1:8002/stt")
    parser.add_argument("--stt-model", default="fast", choices=["fast", "accurate"], help="STT model variant")
    parser.add_argument("--tts-endpoint", default="http://127.0.0.1:8002/tts")
    parser.add_argument("--api-endpoint", default="http://127.0.0.1:8000/voice/ask")
    parser.add_argument("--events-endpoint", default="http://127.0.0.1:8000/events")
    parser.add_argument("--session-state-file", default="arduino\\voice_session.json", help="Session id state file")
    parser.add_argument("--history-turns", type=int, default=6)
    parser.add_argument("--wake-timeout-sec", type=int, default=120)
    parser.add_argument("--start-rms", type=int, default=900)
    parser.add_argument("--stop-rms", type=int, default=500)
    parser.add_argument("--start-frames", type=int, default=2)
    parser.add_argument("--silence-frames", type=int, default=10)
    parser.add_argument("--max-segment-sec", type=float, default=8.0)
    parser.add_argument("--min-segment-sec", type=float, default=0.7)
    parser.add_argument("--pre-roll-frames", type=int, default=8)
    parser.add_argument("--debug-dir", default="arduino\\captures")
    return parser


def open_serial(port: str, baudrate: int):
    import serial

    return serial.Serial(port=port, baudrate=baudrate, timeout=0.25)


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


def normalize_text(text: str) -> str:
    normalized = (text or "").lower().strip()
    normalized = re.sub(r"[\s\.,!?~:;(){}\[\]<>/\\|\-\"'`]+", "", normalized)
    return normalized


def sanitize_tts_text(text: str) -> str:
    value = unicodedata.normalize("NFKC", text or "")
    value = re.sub(r"[\u200b-\u200d\ufeff\ufe0e\ufe0f]", "", value)
    value = re.sub(r"[\x00-\x1f\x7f]", "", value)
    value = re.sub(r"\([^)]*\)", "", value)
    value = re.sub(r"\s+", " ", value)
    value = value.strip()
    value = re.sub(r"^[은는이가을를은는이가을를]+\s*", "", value)
    value = re.sub(r"\s+([,.;:!?])", r"\1", value)
    value = re.sub(r"[ ]{2,}", " ", value)
    return value.strip()


def _is_repeated_chunk(text: str) -> bool:
    if len(text) < 2:
        return False
    max_chunk = min(4, len(text) // 2)
    for size in range(1, max_chunk + 1):
        if len(text) % size != 0:
            continue
        chunk = text[:size]
        if chunk * (len(text) // size) == text:
            return True
    return False


def has_wake_phrase(text: str) -> bool:
    normalized = normalize_text(text)
    if not normalized:
        return False
    for phrase in WAKE_PREFIXES:
        if not normalized.startswith(phrase):
            continue
        suffix = normalized[len(phrase) :]
        if not suffix:
            return True
        if any(suffix.startswith(allowed) for allowed in WAKE_SUFFIXES if allowed):
            return True
    return False


def has_exit_phrase(text: str) -> bool:
    normalized = normalize_text(text)
    return any(phrase in normalized for phrase in EXIT_PHRASES)


def strip_wake_phrase(text: str) -> str:
    raw = (text or "").strip()
    compact = normalize_text(raw)
    for phrase in WAKE_PREFIXES:
        if not compact.startswith(phrase):
            continue
        return raw[len(raw) - len(compact) + len(phrase) :].lstrip(" \t\r\n:,-")
    return raw


def is_noise_transcript(text: str) -> bool:
    normalized = normalize_text(text)
    if not normalized:
        return True
    if re.fullmatch(r"[ㅋㅎㅜㅠ]{2,}", normalized):
        return True
    if normalized in {"음", "어", "아", "네", "응", "예", "흠", "휴", "헉"}:
        return True
    if len(set(normalized)) == 1:
        return True
    if _is_repeated_chunk(normalized) and len(normalized) <= 8:
        return True
    return False


def should_retry_followup(text: str) -> bool:
    if is_noise_transcript(text):
        return True

    normalized = normalize_text(text)
    if not normalized:
        return True

    if re.search(r"[?？]", text):
        return False

    question_cues = (
        "왜",
        "뭐",
        "누구",
        "언제",
        "어디",
        "어떻게",
        "얼마",
        "몇",
        "어떤",
        "궁금",
        "알려줘",
        "말해줘",
        "도와줘",
        "설명",
        "해줘",
        "할까",
        "될까",
        "되나",
        "되니",
        "가능해",
    )
    if any(cue in normalized for cue in question_cues):
        return False

    if len(normalized) <= 1:
        return True

    if _is_repeated_chunk(normalized):
        return True

    return False


def retry_prompt() -> str:
    return "조금만 다시 말해줄래?"


def wav_bytes_from_pcm(pcm_bytes: bytes) -> bytes:
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wav_file:
        wav_file.setnchannels(CHANNELS)
        wav_file.setsampwidth(SAMPLE_WIDTH)
        wav_file.setframerate(SAMPLE_RATE)
        wav_file.writeframes(pcm_bytes)
    return buffer.getvalue()


def save_debug_wav(debug_dir: Path, prefix: str, pcm_bytes: bytes) -> Path:
    debug_dir.mkdir(parents=True, exist_ok=True)
    target = debug_dir / f"{prefix}-{int(time.time() * 1000)}.wav"
    target.write_bytes(wav_bytes_from_pcm(pcm_bytes))
    return target


def post_json(url: str, payload: dict, timeout: int) -> dict:
    data = json.dumps(payload).encode("utf-8")
    request = urlrequest.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urlrequest.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except urlerror.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {exc.code} from {url}: {detail}") from exc


def post_multipart(url: str, field_name: str, filename: str, content: bytes, timeout: int) -> dict:
    boundary = f"----marimo-{uuid.uuid4().hex}"
    mime_type = mimetypes.guess_type(filename)[0] or "application/octet-stream"
    parts = [
        f"--{boundary}\r\n".encode("utf-8"),
        (
            f'Content-Disposition: form-data; name="{field_name}"; filename="{filename}"\r\n'
            f"Content-Type: {mime_type}\r\n\r\n"
        ).encode("utf-8"),
        content,
        b"\r\n",
        f"--{boundary}--\r\n".encode("utf-8"),
    ]
    body = b"".join(parts)
    request = urlrequest.Request(
        url,
        data=body,
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        method="POST",
    )
    try:
        with urlrequest.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except urlerror.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {exc.code} from {url}: {detail}") from exc


class VoicePrototype:
    def __init__(self, args: argparse.Namespace):
        self.args = args
        self.armed_until = 0.0
        self.transcript_buffer = ""
        self.debug_dir = Path(args.debug_dir)
        self.session_state_path = Path(args.session_state_file)
        self.persona_memo = DEFAULT_PERSONA_MEMO
        self.system_memo = DEFAULT_SYSTEM_MEMO
        self.active_session_id: str | None = self.load_session_id()

    def load_session_id(self) -> str | None:
        try:
            if not self.session_state_path.exists():
                return None
            data = json.loads(self.session_state_path.read_text(encoding="utf-8"))
            session_id = str(data.get("session_id", "")).strip()
            if not session_id:
                return None
            uuid.UUID(session_id)
            return session_id or None
        except Exception:
            return None

    def save_session_id(self, session_id: str) -> None:
        self.session_state_path.parent.mkdir(parents=True, exist_ok=True)
        self.session_state_path.write_text(
            json.dumps({"session_id": session_id}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def clear_session_id(self) -> None:
        self.active_session_id = None
        try:
            self.session_state_path.unlink()
        except FileNotFoundError:
            pass
        except OSError:
            pass

    def reset_conversation(self) -> None:
        self.armed_until = 0.0
        self.transcript_buffer = ""

    def ensure_active_session(self) -> str:
        if not self.active_session_id:
            self.active_session_id = str(uuid.uuid4())
            self.save_session_id(self.active_session_id)
            print(f"[session] opened {self.active_session_id}")
        self.touch_remote_session()
        return self.active_session_id

    def touch_remote_session(self) -> None:
        session_id = self.active_session_id
        if not session_id:
            return
        try:
            parsed = urlsplit(self.args.api_endpoint)
            touch_url = urlunsplit((parsed.scheme, parsed.netloc, f"/sessions/{session_id}/touch", "", ""))
            post_json(touch_url, {"touched_by": "serial_voice_proto"}, timeout=30)
        except Exception as exc:
            print(f"[session] touch failed: {exc}")

    def end_active_session(self) -> None:
        session_id = self.active_session_id
        if not session_id:
            return
        try:
            parsed = urlsplit(self.args.api_endpoint)
            end_url = urlunsplit((parsed.scheme, parsed.netloc, f"/sessions/{session_id}/end", "", ""))
            post_json(end_url, {"ended_by": "serial_voice_proto"}, timeout=30)
        except Exception as exc:
            print(f"[session] end failed: {exc}")
        self.clear_session_id()

    def record_event(
        self,
        event_type: str,
        *,
        generated_text: str = "",
        played: bool = False,
        state_level: str = "chat",
        state_alerts: list[str] | None = None,
        sensor: dict[str, object] | None = None,
        distance: float | None = None,
        meta: dict[str, object] | None = None,
        session_id: str | None = None,
    ) -> None:
        resolved_session_id = session_id or self.ensure_active_session()
        payload = {
            "session_id": resolved_session_id,
            "device_id": "serial_voice_proto",
            "trigger_source": "serial_voice_proto",
            "event_type": event_type,
            "generated_text": generated_text,
            "played": played,
            "state_level": state_level,
            "state_alerts": state_alerts or [],
            "meta": meta or {},
        }
        if distance is not None:
            payload["distance"] = distance
        if sensor is not None:
            payload["sensor"] = sensor

        def _send_event() -> None:
            try:
                post_json(self.args.events_endpoint, payload, timeout=15)
            except Exception as exc:
                print(f"[event] {event_type} log failed: {exc}")

        threading.Thread(target=_send_event, daemon=True).start()

    def sanitize_tail(self, text: str) -> str:
        value = (text or "").strip()
        if re.fullmatch(r"[\W_]+", value, flags=re.UNICODE):
            return ""
        return value

    def pick_wake_greeting(self) -> str:
        return random.choice(WAKE_GREETINGS)

    def keep_conversation_open(self, ttl_sec: int | None = None) -> None:
        ttl = ttl_sec if ttl_sec is not None else self.args.wake_timeout_sec
        self.armed_until = time.time() + ttl

    def stt(self, pcm_bytes: bytes) -> str:
        wav_bytes = wav_bytes_from_pcm(pcm_bytes)
        url = f"{self.args.stt_endpoint}?model={self.args.stt_model}"
        payload = post_multipart(url, "audio", "serial.wav", wav_bytes, timeout=60)
        return (payload.get("text") or "").strip()

    def ask_api(self, text: str) -> dict:
        session_id = self.active_session_id or self.ensure_active_session()
        payload = {
            "text": text,
            "use_sensor_context": False,
            "session_id": session_id,
        }
        return post_json(self.args.api_endpoint, payload, timeout=120)

    def tts(self, text: str) -> Path:
        data = json.dumps({"text": text}).encode("utf-8")
        request = urlrequest.Request(
            self.args.tts_endpoint,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urlrequest.urlopen(request, timeout=120) as response:
                payload = response.read()
        except urlerror.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"HTTP {exc.code} from {self.args.tts_endpoint}: {detail}") from exc
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
        try:
            tmp.write(payload)
            return Path(tmp.name)
        finally:
            tmp.close()

    def speak(self, text: str) -> None:
        cleaned_text = sanitize_tts_text(text)
        if not cleaned_text:
            print("[tts] skipped empty sanitized text")
            return
        wav_path = self.tts(cleaned_text)
        try:
            winsound.PlaySound(str(wav_path), winsound.SND_FILENAME)
        finally:
            try:
                wav_path.unlink()
            except OSError:
                pass

    def handle_segment(self, pcm_bytes: bytes) -> None:
        min_bytes = int(self.args.min_segment_sec * SAMPLE_RATE) * SAMPLE_WIDTH
        if len(pcm_bytes) < min_bytes:
            return

        debug_wav = save_debug_wav(self.debug_dir, "segment", pcm_bytes)
        try:
            transcript = self.stt(pcm_bytes)
            print(f"[stt] {transcript or '<empty>'} ({debug_wav.name})")
            self.record_event(
                "stt_completed",
                generated_text=transcript,
                meta={"success": True, "debug_wav": debug_wav.name},
            )
        except Exception as exc:
            self.record_event(
                "stt_completed",
                generated_text="",
                meta={"success": False, "error": str(exc), "debug_wav": debug_wav.name},
            )
            print(f"[stt] failed: {exc}")
            return

        if not transcript:
            return

        if has_exit_phrase(transcript):
            goodbye = "알겠어. 대화를 종료할게. 다음에 또 불러줘."
            print(f"[session] closed by voice {self.active_session_id or '<none>'}")
            try:
                self.speak(goodbye)
                self.record_event(
                    "tts_played",
                    generated_text=goodbye,
                    played=True,
                    meta={"success": True, "kind": "farewell"},
                    session_id=self.ensure_active_session(),
                )
            except Exception as exc:
                self.record_event(
                    "tts_played",
                    generated_text=goodbye,
                    played=False,
                    meta={"success": False, "error": str(exc), "kind": "farewell"},
                    session_id=self.ensure_active_session(),
                )
                print(f"[tts] playback failed: {exc}")
            self.end_active_session()
            self.reset_conversation()
            return

        combined = f"{self.transcript_buffer} {transcript}".strip()
        self.transcript_buffer = combined[-160:]

        if has_wake_phrase(transcript) or has_wake_phrase(self.transcript_buffer):
            if not self.active_session_id:
                self.ensure_active_session()
            self.keep_conversation_open(self.args.wake_timeout_sec)
            self.transcript_buffer = ""
            print("[wake] detected")
            self.record_event(
                "wakeword",
                generated_text=transcript,
                meta={"wake_timeout_sec": self.args.wake_timeout_sec},
            )
            response_text = self.pick_wake_greeting()
            self.speak(response_text)
            self.keep_conversation_open()
            self.record_event(
                "tts_played",
                generated_text=response_text,
                played=True,
                meta={"success": True, "kind": "wake_prompt"},
            )
            return

        if time.time() <= self.armed_until:
            if should_retry_followup(transcript):
                prompt = retry_prompt()
                print("[retry] transcript looks like noise")
                try:
                    self.speak(prompt)
                    self.record_event(
                        "tts_played",
                        generated_text=prompt,
                        played=True,
                        meta={"success": True, "kind": "retry_prompt"},
                    )
                except Exception as exc:
                    self.record_event(
                        "tts_played",
                        generated_text=prompt,
                        played=False,
                        meta={"success": False, "error": str(exc), "kind": "retry_prompt"},
                    )
                    print(f"[tts] playback failed: {exc}")
                self.keep_conversation_open(15)
                return
            self.answer_turn(transcript)
            return

        if self.active_session_id:
            if is_noise_transcript(transcript) or should_retry_followup(transcript):
                print("[idle] transcript ignored outside wake window")
                return
            print("[late] processing transcript outside wake window")
            self.answer_turn(transcript)
            return

    def answer_turn(self, text: str) -> None:
        clean_text = text.strip()
        if not clean_text:
            return
        print(f"[user] {clean_text}")
        try:
            api_result = self.ask_api(clean_text)
        except Exception as exc:
            self.record_event(
                "llm_completed",
                generated_text="",
                meta={"success": False, "error": str(exc), "user_text": clean_text},
            )
            print(f"[error] api request failed: {exc}")
            return

        answer = str(
            api_result.get("answer")
            or api_result.get("tts_text")
            or api_result.get("llm_answer")
            or ""
        ).strip()
        answer = re.sub(r"^(assistant|마리모)\s*[:\-]?\s*", "", answer, flags=re.IGNORECASE)
        answer = sanitize_tts_text(answer)
        if not answer:
            self.record_event(
                "llm_completed",
                generated_text="",
                meta={"success": False, "error": "empty answer", "user_text": clean_text},
            )
            print(f"[error] voice api returned no answer: {api_result}")
            return

        print(f"[agent] session={api_result.get('session_id')}")
        print(f"[marimo] {answer}")
        self.record_event(
            "llm_completed",
            generated_text=answer,
            meta={
                "success": True,
                "interaction_id": api_result.get("interaction_id"),
                "session_id": api_result.get("session_id"),
                "messages_saved": api_result.get("messages_saved"),
            },
        )
        try:
            self.speak(answer)
            self.keep_conversation_open()
            self.record_event(
                "tts_played",
                generated_text=answer,
                played=True,
                meta={"success": True, "answer_source": "voice-server /tts"},
            )
        except Exception as exc:
            self.record_event(
                "tts_played",
                generated_text=answer,
                played=False,
                meta={"success": False, "error": str(exc)},
            )
            print(f"[tts] playback failed: {exc}")
        finally:
            self.keep_conversation_open()


def run_capture_loop(args: argparse.Namespace) -> None:
    prototype = VoicePrototype(args)
    serial_port = open_serial(args.port, args.baudrate)

    pre_roll = collections.deque(maxlen=args.pre_roll_frames)
    active_frames: list[bytes] = []
    active = False
    start_hits = 0
    silence_hits = 0
    max_active_frames = int((args.max_segment_sec * SAMPLE_RATE) / FRAME_SAMPLES)

    print(f"[serial] listening on {args.port} @ {args.baudrate}")
    print(f"[session-state] {args.session_state_file}")
    if prototype.active_session_id:
        print(f"[session] resumed {prototype.active_session_id}")

    try:
        while True:
            frame = serial_port.read(FRAME_BYTES)
            if len(frame) != FRAME_BYTES:
                continue

            rms = compute_rms(frame)

            if not active:
                pre_roll.append(frame)
                if rms >= args.start_rms:
                    start_hits += 1
                else:
                    start_hits = 0

                if start_hits >= args.start_frames:
                    active = True
                    active_frames = list(pre_roll)
                    silence_hits = 0
                    start_hits = 0
                    prototype.record_event(
                        "speech_started",
                        meta={"rms": rms, "start_frames": args.start_frames},
                    )
                continue

            active_frames.append(frame)
            if rms <= args.stop_rms:
                silence_hits += 1
            else:
                silence_hits = 0

            if silence_hits >= args.silence_frames or len(active_frames) >= max_active_frames:
                prototype.record_event(
                    "speech_ended",
                    meta={
                        "frames": len(active_frames),
                        "silence_frames": silence_hits,
                        "max_active_frames": max_active_frames,
                    },
                )
                prototype.handle_segment(b"".join(active_frames))
                active = False
                active_frames = []
                silence_hits = 0
                pre_roll.clear()
    finally:
        serial_port.close()


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    os.makedirs(args.debug_dir, exist_ok=True)
    run_capture_loop(args)


if __name__ == "__main__":
    main()
