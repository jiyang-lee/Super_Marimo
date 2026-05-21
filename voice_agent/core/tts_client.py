import json
import re
import time
import hashlib
from pathlib import Path
import shutil
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
    if json_start != -1 and json_end > json_start:
        json_blob = cleaned[json_start : json_end + 1]
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

    for key in _SPOKEN_TEXT_KEYS:
        match = re.search(rf'"{re.escape(key)}"\s*:\s*"((?:\\.|[^"\\])*)"', cleaned, flags=re.DOTALL)
        if match:
            try:
                return json.loads(f'"{match.group(1)}"')
            except json.JSONDecodeError:
                return match.group(1)

    return cleaned


class TtsClient:
    def __init__(self, api_client: ApiClient, output_dir: str = "/app/shared/audio"):
        self.api_client = api_client
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.cache_dir = self.output_dir / "cache"
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _cache_path(self, text: str, voice_name: Optional[str]) -> Path:
        key = hashlib.sha256(f"{voice_name or ''}\n{text}".encode("utf-8")).hexdigest()
        return self.cache_dir / f"{key}.wav"

    def synthesize_to_file(
        self,
        text: str,
        *,
        voice_name: Optional[str] = None,
        prefix: str = "tts",
    ) -> Path:
        spoken_text = unwrap_spoken_text(text)
        cache_path = self._cache_path(spoken_text, voice_name)
        timestamp = time.time_ns()
        output_path = self.output_dir / f"{prefix}_{timestamp}.wav"
        if cache_path.exists():
            shutil.copyfile(cache_path, output_path)
            return output_path

        wav_bytes = self.api_client.tts(spoken_text, voice_name=voice_name)
        cache_path.write_bytes(wav_bytes)
        output_path.write_bytes(wav_bytes)
        return output_path
