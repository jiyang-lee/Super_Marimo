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
from bridge.core.serial_listener import SerialListener, prune_debug_wavs, wav_bytes_from_pcm
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
        self.audio_player = AudioPlayer(
            args.shared_audio_dir,
            args.poll_interval_ms,
            api_bridge=self.api_bridge,
            on_played=self._on_audio_played,
        )
        self.serial_listener = SerialListener(args)
        self.armed_until = 0.0
        self.distance_followup_until = 0.0
        self.transcript_buffer = ""
        self.persona_memo = DEFAULT_PERSONA_MEMO
        self.system_memo = DEFAULT_SYSTEM_MEMO

    def keep_conversation_open(self, ttl_sec: int | None = None) -> None:
        ttl = ttl_sec if ttl_sec is not None else self.args.wake_timeout_sec
        self.armed_until = time.time() + ttl

    def _on_audio_played(self, filename: str) -> None:
        if filename.startswith("event_proactive_greeting_"):
            ttl = getattr(self.args, "distance_followup_timeout_sec", 30)
            self.distance_followup_until = time.time() + ttl
            print(f"[distance] follow-up window opened for {ttl}s")

    def should_accept_wakeword(self) -> bool:
        try:
            status = self.api_bridge.sensor_runtime_status()
        except Exception as exc:
            print(f"[wake] runtime status unavailable, allowing wakeword: {exc}")
            return True

        settings = status.get("settings") or {}
        if not bool(settings.get("wake_enabled", True)):
            print("[wake] ignored because wake mode is off")
            return False
        if bool(settings.get("distance_detection_enabled", True)) and bool(status.get("distance_inside_threshold")):
            print("[wake] ignored because distance greeting zone is active")
            return False
        return True

    def _is_inside_distance_followup(self) -> bool:
        return time.time() <= self.distance_followup_until

    def _handle_distance_followup(self, transcript: str) -> None:
        if should_retry_followup(transcript):
            prompt = retry_prompt()
            print("[retry] transcript looks like noise (distance followup)")
            try:
                self.api_bridge.ask(prompt, speak=True)
                self.event_logger.log(
                    "tts_played",
                    session_id=self.api_bridge.active_session_id,
                    generated_text=prompt,
                    played=True,
                    meta={"success": True, "kind": "retry_prompt", "context": "distance_followup"},
                )
            except Exception as exc:
                self.event_logger.log(
                    "tts_played",
                    session_id=self.api_bridge.active_session_id,
                    generated_text=prompt,
                    played=False,
                    meta={"success": False, "error": str(exc), "kind": "retry_prompt"},
                )
                print(f"[retry-tts] playback failed: {exc}")
            self.keep_conversation_open(15)
            return

        if has_wake_phrase(transcript):
            stripped = strip_wake_phrase(transcript).strip()
            if stripped:
                print(f"[distance-followup] wake phrase stripped, passing to answer_turn: {stripped}")
                self.answer_turn(stripped)
                return

        self.answer_turn(transcript)

    def _handle_wake(self, transcript: str) -> None:
        if not self.should_accept_wakeword():
            self.transcript_buffer = ""
            return

        self.api_bridge.ensure_session()
        self.keep_conversation_open(self.args.wake_timeout_sec)
        self.transcript_buffer = ""
        self.distance_followup_until = 0.0
        print("[wake] detected")
        self.event_logger.log(
            "wakeword",
            session_id=self.api_bridge.active_session_id,
            generated_text=transcript,
            meta={"wake_timeout_sec": self.args.wake_timeout_sec},
        )

        stripped = strip_wake_phrase(transcript).strip()
        if stripped:
            print(f"[wake] contains question, stripping wake phrase: {stripped}")
            self.answer_turn(stripped)
            return

        response_text = pick_wake_greeting()
        try:
            self.api_bridge.speak(response_text)
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
            print(f"[wake-tts] playback failed: {exc}")
            print("[check] voice-agent logs: docker logs super-marimo-voice-agent")

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
            print("[check] voice-server logs: docker logs super-marimo-voice-server")
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
                print("[check] voice-agent logs: docker logs super-marimo-voice-agent")
            self.api_bridge.end_session()
            self.armed_until = 0.0
            self.distance_followup_until = 0.0
            self.transcript_buffer = ""
            return

        combined = f"{self.transcript_buffer} {transcript}".strip()
        self.transcript_buffer = combined[-160:]

        if self._is_inside_distance_followup():
            self._handle_distance_followup(transcript)
            return

        if has_wake_phrase(transcript) or has_wake_phrase(self.transcript_buffer):
            self._handle_wake(transcript)
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
                    print(f"[retry-tts] playback failed: {exc}")
                self.keep_conversation_open(15)
                return
            self.answer_turn(transcript)
            return

        print("[idle] transcript ignored outside wake window")
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
            print(f"[llm] request failed: {exc}")
            print("[check] api-server logs: docker logs super-marimo-api-server")
            print("[check] voice-agent logs: docker logs super-marimo-voice-agent")
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
            print(f"[llm] voice api returned no answer: {api_result}")
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
        prune_debug_wavs(Path(self.args.debug_dir), "segment", int(getattr(self.args, "debug_retain_count", 25)))
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
