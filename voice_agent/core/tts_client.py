import time
from pathlib import Path
from typing import Optional

from core.api_client import ApiClient


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
        wav_bytes = self.api_client.tts(text, voice_name=voice_name)
        timestamp = time.time_ns()
        output_path = self.output_dir / f"{prefix}_{timestamp}.wav"
        output_path.write_bytes(wav_bytes)
        return output_path
