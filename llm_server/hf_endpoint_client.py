from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from typing import Any


class HfEndpointError(RuntimeError):
    pass


HF_LLM_RUNTIME_STATE: dict[str, Any] = {
    "ready": False,
    "backend": None,
    "model": None,
    "last_latency_ms": None,
    "last_error": None,
}


def post_json(endpoint_url: str, payload: dict[str, Any], *, token: str | None, timeout: float) -> tuple[Any, float]:
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    body = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(endpoint_url, data=body, headers=headers, method="POST")
    started = time.perf_counter()
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read()
            latency_ms = (time.perf_counter() - started) * 1000
            content_type = response.headers.get("Content-Type", "")
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise HfEndpointError(f"HF endpoint HTTP {exc.code}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise HfEndpointError(f"HF endpoint request failed: {exc}") from exc

    if "application/json" not in content_type:
        return raw.decode("utf-8", errors="replace"), latency_ms
    try:
        return json.loads(raw.decode("utf-8")), latency_ms
    except json.JSONDecodeError as exc:
        raise HfEndpointError(f"HF endpoint returned invalid JSON: {exc}") from exc


def extract_text(payload: Any) -> str:
    if hasattr(payload, "model_dump"):
        payload = payload.model_dump()
    elif hasattr(payload, "dict"):
        payload = payload.dict()
    elif not isinstance(payload, (str, list, dict)) and hasattr(payload, "__dict__"):
        payload = vars(payload)

    if isinstance(payload, str):
        return payload.strip()
    if isinstance(payload, list) and payload:
        return extract_text(payload[0])
    if not isinstance(payload, dict):
        return str(payload or "").strip()

    choices = payload.get("choices")
    if isinstance(choices, list) and choices:
        first = choices[0]
        if isinstance(first, dict):
            message = first.get("message")
            if isinstance(message, dict):
                return str(message.get("content") or "").strip()
            return str(first.get("text") or "").strip()

    for key in ("generated_text", "text", "answer", "content", "output"):
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
        if isinstance(value, list) and value:
            return extract_text(value)

    return ""


def chat_completion(
    *,
    base_url: str,
    api_key: str,
    model: str,
    messages: list[dict[str, str]],
    max_tokens: int,
    timeout: float,
) -> tuple[Any, float]:
    from openai import OpenAI

    client = OpenAI(base_url=base_url, api_key=api_key, timeout=timeout)
    started = time.perf_counter()
    completion = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=0,
        max_tokens=max_tokens,
    )
    latency_ms = (time.perf_counter() - started) * 1000
    return completion, latency_ms
