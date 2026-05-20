from typing import Any, Optional

import requests


class ApiClient:
    def __init__(
        self,
        api_server_url: str,
        voice_server_url: str,
        llm_server_url: str,
        timeout: float = 120.0,
    ):
        self.api_server_url = api_server_url.rstrip("/")
        self.voice_server_url = voice_server_url.rstrip("/")
        self.llm_server_url = llm_server_url.rstrip("/")
        self.timeout = timeout

    def get_json(self, url: str, timeout: Optional[float] = None) -> dict[str, Any]:
        response = requests.get(url, timeout=timeout or self.timeout)
        response.raise_for_status()
        return response.json()

    def post_json(self, url: str, payload: dict[str, Any], timeout: Optional[float] = None) -> dict[str, Any]:
        response = requests.post(url, json=payload, timeout=timeout or self.timeout)
        response.raise_for_status()
        return response.json()

    def put_json(self, url: str, payload: dict[str, Any], timeout: Optional[float] = None) -> dict[str, Any]:
        response = requests.put(url, json=payload, timeout=timeout or self.timeout)
        response.raise_for_status()
        return response.json()

    # API Server
    def api_health(self) -> dict[str, Any]:
        return self.get_json(f"{self.api_server_url}/health", timeout=10)

    def list_events(
        self,
        *,
        event_type: Optional[str] = None,
        event_types: Optional[list[str]] = None,
        status: Optional[str] = None,
        played: Optional[bool] = False,
        limit: int = 10,
        order: str = "desc",
    ) -> dict[str, Any]:
        params: dict[str, Any] = {"limit": limit}
        if event_type:
            params["event_type"] = event_type
        if event_types:
            params["event_types"] = event_types
        if status:
            params["status"] = status
        if played is not None:
            params["played"] = str(played).lower()
        if order:
            params["order"] = order
        response = requests.get(f"{self.api_server_url}/events", params=params, timeout=10)
        response.raise_for_status()
        return response.json()

    def mark_event_played(self, event_id: int) -> dict[str, Any]:
        return self.post_json(
            f"{self.api_server_url}/events/{event_id}/played",
            {},
            timeout=10,
        )

    def update_event_status(self, event_id: int, status: str) -> dict[str, Any]:
        return self.put_json(
            f"{self.api_server_url}/events/{event_id}/status",
            {"status": status},
            timeout=10,
        )

    def save_session_message(
        self,
        session_id: str,
        role: str,
        content: str,
        meta: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        return self.post_json(
            f"{self.api_server_url}/sessions/{session_id}/messages",
            {"role": role, "content": content, "meta": meta or {}},
            timeout=10,
        )

    def voice_ask(
        self,
        text: str,
        session_id: Optional[str] = None,
        persona_memo: Optional[str] = None,
        system_memo: Optional[str] = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "text": text,
            "session_id": session_id,
            "use_sensor_context": False,
        }
        if persona_memo:
            payload["persona_memo"] = persona_memo
        if system_memo:
            payload["system_memo"] = system_memo
        return self.post_json(f"{self.api_server_url}/voice/ask", payload)

    # Voice Server
    def tts(self, text: str, voice_name: Optional[str] = None) -> bytes:
        payload: dict[str, Any] = {"text": text}
        if voice_name:
            payload["voice_name"] = voice_name
        response = requests.post(
            f"{self.voice_server_url}/tts",
            json=payload,
            timeout=self.timeout,
        )
        response.raise_for_status()
        return response.content

    def voice_health(self) -> dict[str, Any]:
        return self.get_json(f"{self.voice_server_url}/health", timeout=10)

    def voice_ready(self) -> dict[str, Any]:
        return self.get_json(f"{self.voice_server_url}/ready", timeout=10)

    # LLM Server
    def llm_generate(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self.post_json(f"{self.llm_server_url}/generate", payload)

    def llm_health(self) -> dict[str, Any]:
        return self.get_json(f"{self.llm_server_url}/health", timeout=10)

    def llm_ready(self) -> dict[str, Any]:
        return self.get_json(f"{self.llm_server_url}/ready", timeout=10)
