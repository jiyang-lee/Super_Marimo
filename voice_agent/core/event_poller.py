import logging
import threading
import time
from typing import Any, Optional

from core.api_client import ApiClient
from core.tts_client import TtsClient

logger = logging.getLogger("voice_agent.event_poller")


class EventPoller:
    def __init__(
        self,
        api_client: ApiClient,
        tts_client: TtsClient,
        interval_sec: float = 1.0,
        event_types: Optional[list[str]] = None,
    ):
        self.api_client = api_client
        self.tts_client = tts_client
        self.interval_sec = interval_sec
        self.event_types = event_types or ["proactive_greeting", "sensor_warning"]
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()

    def start(self) -> None:
        if self._thread is not None and self._thread.is_alive():
            logger.warning("EventPoller already running")
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        logger.info("EventPoller started (interval=%ss, types=%s)", self.interval_sec, self.event_types)

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=5.0)
            logger.info("EventPoller stopped")

    def _run(self) -> None:
        while not self._stop_event.is_set():
            try:
                self._poll_once()
            except Exception as exc:
                logger.exception("EventPoller poll error: %s", exc)
            self._stop_event.wait(self.interval_sec)

    def _poll_once(self) -> None:
        while True:
            try:
                result = self.api_client.list_events(
                    event_types=self.event_types,
                    played=False,
                    limit=1,
                    order="asc",
                )
                events = result.get("events") or []
                if not events:
                    return

                event = events[0]
                event_id = event["event_id"]
                event_type = str(event.get("event_type") or "event")
                generated_text = str(event.get("generated_text") or "").strip()

                if not generated_text:
                    logger.warning("Event %s has no generated_text, marking played", event_id)
                    self.api_client.mark_event_played(event_id)
                    continue

                logger.info("Processing event %s (%s): %s", event_id, event_type, generated_text[:40])
                try:
                    self.tts_client.synthesize_to_file(
                        generated_text,
                        prefix=f"event_{event_type}_{event_id}",
                    )
                except Exception:
                    logger.exception("TTS synthesis failed for event %s (%s)", event_id, event_type)
                finally:
                    self.api_client.mark_event_played(event_id)
                    logger.info("Event %s marked as played", event_id)

            except Exception as exc:
                logger.exception("EventPoller poll error: %s", exc)
                return
