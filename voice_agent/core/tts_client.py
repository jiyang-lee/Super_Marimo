import json
import re
import time
from pathlib import Path
from typing import Optional

from core.api_client import ApiClient

_SPOKEN_TEXT_KEYS = ("answer", "tts_text", "llm_answer", "response", "text", "content")


def unwrap_spoken_text(text: str) -> str:
    cleaned = str(text or "").strip()
    if not cleaned:
        return ""

    cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", cleaned, flags=re.IGNORECASE | re.DOTALL).strip()
    json_start = cleaned.find("{")
    json_end = cleaned.rfind("}")
    if json_start != -1:
        json_blob = cleaned[json_start : json_end + 1] if json_end > json_start else cleaned[json_start:]
        try:
            parsed = json.loads(json_blob)
        except json.JSONDecodeError:
            parsed = None
        if isinstance(parsed, dict):
            for key in _SPOKEN_TEXT_KEYS:
                value = parsed.get(key)
                if isinstance(value, str) and value.strip():
                    return value.strip()
            for key in _SPOKEN_TEXT_KEYS:
                value = parsed.get(key)
                if value not in (None, ""):
                    return str(value).strip()

    return cleaned


class TtsClient:
    def __init__(self, api_client: ApiClient, output_dir: str = "/app/shared/audio"):
        self.api_client = api_client
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def synthesize_to_file(
        self,
        text: str,
        *,
        voice_name: Optional[str] = None,
        prefix: str = "tts",
    ) -> Path:
        spoken_text = unwrap_spoken_text(text)
        wav_bytes = self.api_client.tts(spoken_text, voice_name=voice_name)
        timestamp = time.time_ns()
        output_path = self.output_dir / f"{prefix}_{timestamp}.wav"
        output_path.write_bytes(wav_bytes)
        return output_path
