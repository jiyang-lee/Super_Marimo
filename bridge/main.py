from __future__ import annotations

import os
import re
import threading
import time
import unicodedata
from pathlib import Path

from bridge.config import build_parser, DEFAULT_PERSONA_MEMO, DEFAULT_SYSTEM_MEMO
from bridge.core.api_bridge import ApiBridge
from bridge.core.audio_player import AudioPlayer
from bridge.core.event_logger import EventLogger
from bridge.core.serial_listener import SerialListener, wav_bytes_from_pcm
from bridge.core.stt_client import SttClient
from bridge.core.vad_wake import (
    has_exit_phrase,
    has_wake_phrase,
    is_noise_transcript,
    pick_wake_greeting,
    retry_prompt,
    should_retry_followup,
    strip_wake_phrase,
)


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


class Bridge:
    def __init__(self, args: Any):
        self.args = args
        self.api_bridge = ApiBridge(args.voice_agent_url, args.api_server_url)
        self.stt_client = SttClient(args.stt_endpoint, args.stt_model)
        self.event_logger = EventLogger(args.events_endpoint)
        self.audio_player = AudioPlayer(args.shared_audio_dir, args.poll_interval_ms)
        self.serial_listener = SerialListener(args)
        self.armed_until = 0.0
        self.transcript_buffer = ""
        self.persona_memo = DEFAULT_PERSONA_MEMO
        self.system_memo = DEFAULT_SYSTEM_MEMO

    def keep_conversation_open(self, ttl_sec: int | None = None) -> None:
        ttl = ttl_sec if ttl_sec is not None else self.args.wake_timeout_sec
        self.armed_until = time.time() + ttl

    def handle_segment(self, pcm_bytes: bytes) -> None:
        min_bytes = int(self.args.min_segment_sec * 16000) * 2
        if len(pcm_bytes) < min_bytes:
            return

        wav_bytes = wav_bytes_from_pcm(pcm_bytes)

        try:
            transcript = self.stt_client.transcribe(wav_bytes)
            print(f"[stt] {transcript or '<empty>'}")
            self.event_logger.log(
                "stt_completed",
                session_id=self.api_bridge.active_session_id,
                generated_text=transcript,
                meta={"success": True},
            )
        except Exception as exc:
            self.event_logger.log(
                "stt_completed",
                session_id=self.api_bridge.active_session_id,
                generated_text="",
                meta={"success": False, "error": str(exc)},
            )
            print(f"[stt] failed: {exc}")
            return

        if not transcript:
            return

        if has_exit_phrase(transcript):
            goodbye = "알겠어. 대화를 종료할게. 다음에 또 불러줘."
            print(f"[session] closed by voice {self.api_bridge.active_session_id or '<none>'}")
            try:
                self.api_bridge.ask(goodbye, speak=True)
                self.event_logger.log(
                    "tts_played",
                    session_id=self.api_bridge.active_session_id,
                    generated_text=goodbye,
                    played=True,
                    meta={"success": True, "kind": "farewell"},
                )
            except Exception as exc:
                self.event_logger.log(
                    "tts_played",
                    session_id=self.api_bridge.active_session_id,
                    generated_text=goodbye,
                    played=False,
                    meta={"success": False, "error": str(exc), "kind": "farewell"},
                )
                print(f"[tts] playback failed: {exc}")
            self.api_bridge.end_session()
            self.armed_until = 0.0
            self.transcript_buffer = ""
            return

        combined = f"{self.transcript_buffer} {transcript}".strip()
        self.transcript_buffer = combined[-160:]

        if has_wake_phrase(transcript) or has_wake_phrase(self.transcript_buffer):
            self.api_bridge.ensure_session()
            self.keep_conversation_open(self.args.wake_timeout_sec)
            self.transcript_buffer = ""
            print("[wake] detected")
            self.event_logger.log(
                "wakeword",
                session_id=self.api_bridge.active_session_id,
                generated_text=transcript,
                meta={"wake_timeout_sec": self.args.wake_timeout_sec},
            )
            response_text = pick_wake_greeting()
            try:
                self.api_bridge.ask(response_text, speak=True)
                self.keep_conversation_open()
                self.event_logger.log(
                    "tts_played",
                    session_id=self.api_bridge.active_session_id,
                    generated_text=response_text,
                    played=True,
                    meta={"success": True, "kind": "wake_prompt"},
                )
            except Exception as exc:
                self.event_logger.log(
                    "tts_played",
                    session_id=self.api_bridge.active_session_id,
                    generated_text=response_text,
                    played=False,
                    meta={"success": False, "error": str(exc), "kind": "wake_prompt"},
                )
                print(f"[tts] playback failed: {exc}")
            return

        if time.time() <= self.armed_until:
            if should_retry_followup(transcript):
                prompt = retry_prompt()
                print("[retry] transcript looks like noise")
                try:
                    self.api_bridge.ask(prompt, speak=True)
                    self.event_logger.log(
                        "tts_played",
                        session_id=self.api_bridge.active_session_id,
                        generated_text=prompt,
                        played=True,
                        meta={"success": True, "kind": "retry_prompt"},
                    )
                except Exception as exc:
                    self.event_logger.log(
                        "tts_played",
                        session_id=self.api_bridge.active_session_id,
                        generated_text=prompt,
                        played=False,
                        meta={"success": False, "error": str(exc), "kind": "retry_prompt"},
                    )
                    print(f"[tts] playback failed: {exc}")
                self.keep_conversation_open(15)
                return
            self.answer_turn(transcript)
            return

        if self.api_bridge.active_session_id:
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
            api_result = self.api_bridge.ask(clean_text, speak=True)
        except Exception as exc:
            self.event_logger.log(
                "llm_completed",
                session_id=self.api_bridge.active_session_id,
                generated_text="",
                meta={"success": False, "error": str(exc), "user_text": clean_text},
            )
            print(f"[error] api request failed: {exc}")
            return

        answer = str(api_result.get("answer") or "").strip()
        answer = re.sub(r"^(assistant|마리모)\s*[:\-]?\s*", "", answer, flags=re.IGNORECASE)
        answer = sanitize_tts_text(answer)
        if not answer:
            self.event_logger.log(
                "llm_completed",
                session_id=self.api_bridge.active_session_id,
                generated_text="",
                meta={"success": False, "error": "empty answer", "user_text": clean_text},
            )
            print(f"[error] voice api returned no answer: {api_result}")
            return

        print(f"[agent] session={api_result.get('session_id')}")
        print(f"[marimo] {answer}")
        self.event_logger.log(
            "llm_completed",
            session_id=self.api_bridge.active_session_id,
            generated_text=answer,
            meta={
                "success": True,
                "interaction_id": api_result.get("interaction_id"),
                "session_id": api_result.get("session_id"),
                "messages_saved": api_result.get("messages_saved"),
            },
        )
        self.event_logger.log(
            "tts_played",
            session_id=self.api_bridge.active_session_id,
            generated_text=answer,
            played=True,
            meta={"success": True, "answer_source": "voice-agent"},
        )
        self.keep_conversation_open()

    def run(self) -> None:
        os.makedirs(self.args.debug_dir, exist_ok=True)
        os.makedirs(self.args.shared_audio_dir, exist_ok=True)

        # Start audio player in background thread
        audio_thread = threading.Thread(target=self.audio_player.start, daemon=True)
        audio_thread.start()

        if self.api_bridge.active_session_id:
            print(f"[session] resumed {self.api_bridge.active_session_id}")

        self.serial_listener.run(
            on_segment=self.handle_segment,
            on_speech_started=lambda rms: self.event_logger.log(
                "speech_started",
                session_id=self.api_bridge.active_session_id,
                meta={"rms": rms},
            ),
            on_speech_ended=lambda frames, silence, max_frames: self.event_logger.log(
                "speech_ended",
                session_id=self.api_bridge.active_session_id,
                meta={"frames": frames, "silence_frames": silence, "max_active_frames": max_frames},
            ),
        )


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    bridge = Bridge(args)
    bridge.run()


if __name__ == "__main__":
    main()
