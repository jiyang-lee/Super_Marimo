import json
import os
from pathlib import Path
from typing import Optional


class SessionStore:
    def __init__(self, session_file: str = "/tmp/super_marimo_voice_agent_session.json"):
        self.session_file = Path(session_file)

    def load(self) -> Optional[str]:
        try:
            if not self.session_file.exists():
                return None
            payload = json.loads(self.session_file.read_text(encoding="utf-8"))
            session_id = str(payload.get("session_id", "")).strip()
            return session_id or None
        except Exception:
            return None

    def save(self, session_id: str) -> None:
        self.session_file.parent.mkdir(parents=True, exist_ok=True)
        self.session_file.write_text(
            json.dumps({"session_id": session_id}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def clear(self) -> None:
        try:
            self.session_file.unlink()
        except FileNotFoundError:
            pass
