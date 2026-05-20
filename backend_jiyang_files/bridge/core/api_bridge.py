import json
import uuid
from pathlib import Path
from typing import Any, Optional
from urllib import error as urlerror
from urllib import request as urlrequest


class ApiBridge:
    def __init__(self, voice_agent_url: str, api_server_url: str):
        self.voice_agent_url = voice_agent_url.rstrip("/")
        self.api_server_url = api_server_url.rstrip("/")
        self.session_state_path = Path("bridge/session.json")
        self.active_session_id: Optional[str] = self._load_session_id()

    def _load_session_id(self) -> Optional[str]:
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

    def _save_session_id(self, session_id: str) -> None:
        self.session_state_path.parent.mkdir(parents=True, exist_ok=True)
        self.session_state_path.write_text(
            json.dumps({"session_id": session_id}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def clear_session(self) -> None:
        self.active_session_id = None
        try:
            self.session_state_path.unlink()
        except FileNotFoundError:
            pass

    def ensure_session(self) -> str:
        if not self.active_session_id:
            self.active_session_id = str(uuid.uuid4())
            self._save_session_id(self.active_session_id)
            print(f"[session] opened {self.active_session_id}")
        self._touch_session()
        return self.active_session_id

    def _touch_session(self) -> None:
        if not self.active_session_id:
            return
        try:
            url = f"{self.api_server_url}/sessions/{self.active_session_id}/touch"
            _post_json(url, {"touched_by": "bridge"}, timeout=30)
        except Exception as exc:
            print(f"[session] touch failed: {exc}")

    def end_session(self) -> None:
        if not self.active_session_id:
            return
        try:
            url = f"{self.api_server_url}/sessions/{self.active_session_id}/end"
            _post_json(url, {"ended_by": "bridge"}, timeout=30)
        except Exception as exc:
            print(f"[session] end failed: {exc}")
        self.clear_session()

    def ask(self, text: str, speak: bool = True) -> dict[str, Any]:
        session_id = self.ensure_session()
        url = f"{self.voice_agent_url}/ask"
        payload = {
            "text": text,
            "session_id": session_id,
            "speak": speak,
        }
        result = _post_json(url, payload, timeout=120)
        resolved = str(result.get("session_id") or session_id)
        self._save_session_id(resolved)
        self.active_session_id = resolved
        return result

    def speak(self, text: str, save_message: bool = True) -> dict[str, Any]:
        session_id = self.ensure_session()
        url = f"{self.voice_agent_url}/speak"
        payload = {
            "text": text,
            "session_id": session_id,
            "save_message": save_message,
        }
        result = _post_json(url, payload, timeout=120)
        resolved = str(result.get("session_id") or session_id)
        self._save_session_id(resolved)
        self.active_session_id = resolved
        return result

    def update_event_status(self, event_id: int, status: str) -> dict[str, Any]:
        url = f"{self.api_server_url}/events/{event_id}/status"
        return _put_json(url, {"status": status}, timeout=10)

    def sensor_runtime_status(self) -> dict[str, Any]:
        latest = _get_json(f"{self.api_server_url}/sensor/latest", timeout=10)
        settings = latest.get("runtime_settings") or {}
        return {
            "settings": settings,
            "distance_inside_threshold": bool(latest.get("distance_inside_threshold")),
        }


def _post_json(url: str, payload: dict[str, Any], timeout: int) -> dict[str, Any]:
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


def _put_json(url: str, payload: dict[str, Any], timeout: int) -> dict[str, Any]:
    data = json.dumps(payload).encode("utf-8")
    request = urlrequest.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="PUT",
    )
    try:
        with urlrequest.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except urlerror.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {exc.code} from {url}: {detail}") from exc


def _get_json(url: str, timeout: int) -> dict[str, Any]:
    request = urlrequest.Request(url, headers={"Accept": "application/json"}, method="GET")
    try:
        with urlrequest.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except urlerror.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {exc.code} from {url}: {detail}") from exc
