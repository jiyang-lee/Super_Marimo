from __future__ import annotations

import os
import json
import re
import threading
import time
import unicodedata
from pathlib import Path
from typing import Any, Optional

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
    value = unwrap_spoken_text(value)
    value = re.sub(r"[\u200b-\u200d\ufeff\ufe0e\ufe0f]", "", value)
    value = re.sub(r"[\x00-\x1f\x7f]", "", value)
    value = re.sub(r"\([^)]*\)", "", value)
    value = re.sub(r"\s+", " ", value)
    value = value.strip()
    value = re.sub(r"^[??붿씠媛?꾨???붿씠媛?꾨?]+\s*", "", value)
    value = re.sub(r"\s+([,.;:!?])", r"\1", value)
    value = re.sub(r"[ ]{2,}", " ", value)
    return value.strip()


def unwrap_spoken_text(text: str) -> str:
    value = (text or "").strip()
    if not value:
        return ""
    value = re.sub(r"^```(?:json)?\s*|\s*```$", "", value, flags=re.IGNORECASE | re.DOTALL).strip()
    json_start = value.find("{")
    json_end = value.rfind("}")
    if json_start != -1 and json_end > json_start:
        json_blob = value[json_start : json_end + 1]
        try:
            parsed = json.loads(json_blob)
        except json.JSONDecodeError:
            parsed = None
        if isinstance(parsed, dict):
            for key in ("answer", "tts_text", "llm_answer", "response", "text", "content"):
                candidate = parsed.get(key)
                if isinstance(candidate, str) and candidate.strip():
                    return candidate.strip()
            for key in ("answer", "tts_text", "llm_answer", "response", "text", "content"):
                candidate = parsed.get(key)
                if candidate not in (None, ""):
                    return str(candidate).strip()

    for key in ("answer", "tts_text", "llm_answer", "response", "text", "content"):
        match = re.search(rf'"{re.escape(key)}"\s*:\s*"((?:\\.|[^"\\])*)"', value, flags=re.DOTALL)
        if match:
            try:
                return json.loads(f'"{match.group(1)}"')
            except json.JSONDecodeError:
                return match.group(1)
    return value


def strip_answer_prefix(text: str) -> str:
    value = (text or "").strip()
    lowered = value.lower()
    for prefix in ("assistant", "marimo", "마리모"):
        if lowered.startswith(prefix):
            value = value[len(prefix):].lstrip(" \t\r\n:;-")
            break
    return value


def is_meaningful_text(text: str) -> bool:
    compact = re.sub(r"[\s\.,!?~:;(){}\[\]<>/\\|\-\"'`]+", "", (text or "").strip())
    return len(compact) > 1


class Bridge:
    def __init__(self, args: Any):
        self.args = args
        self.api_bridge = ApiBridge(args.voice_agent_url, args.api_server_url, args.session_state_file)
        self.stt_client = SttClient(args.stt_endpoint, args.stt_model)
        self.event_logger = EventLogger(args.events_endpoint)
        self.audio_player = AudioPlayer(
            args.shared_audio_dir,
            args.poll_interval_ms,
            api_bridge=self.api_bridge,
            on_playing=self._on_audio_playing,
            on_played=self._on_audio_played,
            should_suppress_proactive=self.should_suppress_proactive_audio,
            is_web_mode=self.is_web_voice_mode,
        )
        
        # ?ㅻ뵒???낅젰 ?뚯뒪 ?꾪솚 吏??(serial ?먮뒗 mic)
        self.source_type = getattr(args, "source", "serial")
        if self.source_type == "mic":
            from bridge.core.microphone_listener import MicrophoneListener
            self.audio_listener = MicrophoneListener(args)
            print("[bridge] Configured to use local microphone as input source.")
        else:
            self.audio_listener = SerialListener(args)
            print(f"[bridge] Configured to use serial port {args.port} as input source.")
            
        self.armed_until = 0.0
        self.distance_followup_until = 0.0
        self.reply_window_until = 0.0
        self.suppress_next_reply_boost = False
        self.tts_mute_until = 0.0
        self.transcript_buffer = ""
        self.persona_memo = DEFAULT_PERSONA_MEMO
        self.system_memo = DEFAULT_SYSTEM_MEMO

    def keep_conversation_open(self, ttl_sec: int | None = None) -> None:
        ttl = ttl_sec if ttl_sec is not None else self.args.wake_timeout_sec
        self.armed_until = time.time() + ttl

    def _on_audio_playing(self, filename: str, duration_sec: float | None = None) -> None:
        if filename.startswith("ask_") or filename.startswith("speak_") or filename.startswith("event_proactive_greeting_"):
            current = float(getattr(self, "tts_mute_until", 0.0))
            playback_sec = float(duration_sec or 0.0)
            self.tts_mute_until = max(current, time.time() + playback_sec + 0.2)

    def _on_audio_played(self, filename: str) -> None:
        if self.is_web_voice_mode():
            self.clear_voice_windows()
            print(f"[mode] web voice enabled; bridge audio ignored after {filename}")
            return
        if filename.startswith("event_proactive_greeting_"):
            ttl = getattr(self.args, "distance_followup_timeout_sec", 30)
            self.distance_followup_until = time.time() + ttl
            print(f"[distance] follow-up window opened for {ttl}s")
        if self.suppress_next_reply_boost:
            if filename.startswith("ask_") or filename.startswith("speak_"):
                self.suppress_next_reply_boost = False
            return
        if filename.startswith("event_proactive_greeting_") or filename.startswith("ask_") or filename.startswith("speak_"):
            ttl = getattr(self.args, "reply_boost_sec", 12)
            self.reply_window_until = time.time() + ttl
            print(f"[listen] reply window opened for {ttl}s after {filename}")
            current = float(getattr(self, "tts_mute_until", 0.0))
            self.tts_mute_until = max(current, time.time() + 0.25)

    def should_accept_wakeword(self) -> bool:
        try:
            status = self.api_bridge.sensor_runtime_status()
        except Exception as exc:
            print(f"[wake] runtime status unavailable, blocking wakeword: {exc}")
            return False

        settings = status.get("settings") or {}
        if not bool(settings.get("wake_enabled", True)):
            print("[wake] ignored because wake mode is off")
            return False
        if bool(settings.get("web_voice_enabled", False)):
            print("[wake] ignored because web voice mode is on")
            return False
        if not bool(status.get("wake_eligible")):
            print("[wake] ignored because distance is below threshold")
            return False
        return True

    def is_web_voice_mode(self) -> bool:
        try:
            status = self.api_bridge.sensor_runtime_status()
        except Exception as exc:
            print(f"[mode] runtime status unavailable, bridge voice gate open: {exc}")
            return False
        settings = status.get("settings") or {}
        return bool(settings.get("web_voice_enabled", False))

    def should_suppress_proactive_audio(self) -> bool:
        return self.is_web_voice_mode() or self.is_conversation_active()

    def clear_voice_windows(self) -> None:
        self.armed_until = 0.0
        self.distance_followup_until = 0.0
        self.reply_window_until = 0.0
        self.transcript_buffer = ""

    def is_spurious_english_transcript(self, transcript: str) -> bool:
        value = re.sub(r"\s+", " ", (transcript or "").strip().lower())
        value = value.strip(" .,!?:;\"'")
        if re.search(r"[가-힣]", value):
            return False
        common_noise = {
            "you",
            "thank you",
            "thanks",
            "would you reserve a seat",
            "reserve a seat",
        }
        return value in common_noise

    def _is_inside_distance_followup(self) -> bool:
        return time.time() <= self.distance_followup_until

    def is_conversation_active(self) -> bool:
        now = time.time()
        return now <= self.armed_until or now <= self.distance_followup_until or now <= self.reply_window_until

    def is_reply_boost_active(self) -> bool:
        return self.is_conversation_active()

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
            if is_meaningful_text(stripped):
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
        if is_meaningful_text(stripped):
            print(f"[wake] contains question, stripping wake phrase: {stripped}")
            self.answer_turn(stripped)
            return

        response_text = pick_wake_greeting()
        try:
            # Wake Greeting ?몄궗??寃쎌슦 save_message=False瑜??섍꺼 ?몄뀡 硫붿떆吏 DB??以묐났 ?꾩쟻?섏? ?딅룄濡??꾪꽣留?
            self.api_bridge.speak(response_text, save_message=False)
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
        if self.is_web_voice_mode():
            self.clear_voice_windows()
            print("[mode] web voice enabled; bridge voice ignored")
            return

        if time.time() <= float(getattr(self, "tts_mute_until", 0.0)):
            print("[stt] skipped during tts playback")
            return

        min_segment_sec = float(self.args.min_segment_sec)
        if self.is_reply_boost_active():
            min_segment_sec = min(min_segment_sec, float(getattr(self.args, "reply_min_segment_sec", min_segment_sec)))
        else:
            min_segment_sec = min(min_segment_sec, float(getattr(self.args, "wake_min_segment_sec", min_segment_sec)))
        min_bytes = int(min_segment_sec * 16000) * 2
        if len(pcm_bytes) < min_bytes:
            print(f"[stt] skipped short segment ({len(pcm_bytes)} bytes < {min_bytes})")
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

        if self.is_spurious_english_transcript(transcript):
            print(f"[stt] ignored likely HF hallucination: {transcript}")
            return

        if has_exit_phrase(transcript):
            print(f"[session] closed by voice {self.api_bridge.active_session_id or '<none>'}")
            self.api_bridge.end_session()
            self.armed_until = 0.0
            self.distance_followup_until = 0.0
            self.reply_window_until = 0.0
            self.suppress_next_reply_boost = False
            self.tts_mute_until = 0.0
            self.transcript_buffer = ""
            if hasattr(self, "audio_player"):
                self.audio_player.suppress_proactive_for(getattr(self.args, "distance_followup_timeout_sec", 30))
            return

        combined = f"{self.transcript_buffer} {transcript}".strip()
        self.transcript_buffer = combined[-160:]

        if self._is_inside_distance_followup():
            self._handle_distance_followup(transcript)
            return

        if has_wake_phrase(transcript) or has_wake_phrase(self.transcript_buffer):
            self._handle_wake(transcript)
            return

        if self.is_reply_boost_active():
            self.answer_turn(transcript)
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

        answer = strip_answer_prefix(str(api_result.get("answer") or ""))
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
        current_mute = float(getattr(self, "tts_mute_until", 0.0))
        preplay_guard = float(getattr(self.args, "tts_preplay_guard_sec", 0.35))
        self.tts_mute_until = max(current_mute, time.time() + preplay_guard)
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
        self.keep_conversation_open(self.args.wake_timeout_sec)

    def run(self) -> None:
        os.makedirs(self.args.debug_dir, exist_ok=True)
        prune_debug_wavs(Path(self.args.debug_dir), "segment", int(getattr(self.args, "debug_retain_count", 25)))
        os.makedirs(self.args.shared_audio_dir, exist_ok=True)

        # Start audio player in background thread
        audio_thread = threading.Thread(target=self.audio_player.start, daemon=True)
        audio_thread.start()

        if self.api_bridge.active_session_id:
            print(f"[session] resumed {self.api_bridge.active_session_id}")

        self.audio_listener.run(
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
            is_boosted=self.is_reply_boost_active,
        )


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    bridge = Bridge(args)
    bridge.run()


if __name__ == "__main__":
    main()

