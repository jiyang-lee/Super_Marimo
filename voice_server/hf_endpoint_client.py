from __future__ import annotations

import base64
import json
import time
import urllib.error
import urllib.request
from typing import Any


class HfEndpointError(RuntimeError):
    pass


def _headers(token: str | None, content_type: str) -> dict[str, str]:
    headers = {"Content-Type": content_type}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def post_json(endpoint_url: str, payload: dict[str, Any], *, token: str | None, timeout: float) -> tuple[Any, float]:
    body = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(endpoint_url, data=body, headers=_headers(token, "application/json"), method="POST")
    return _read_response(request, timeout)


def post_bytes(
    endpoint_url: str,
    payload: bytes,
    *,
    token: str | None,
    timeout: float,
    content_type: str = "audio/wav",
) -> tuple[Any, float]:
    request = urllib.request.Request(endpoint_url, data=payload, headers=_headers(token, content_type), method="POST")
    return _read_response(request, timeout)


def _read_response(request: urllib.request.Request, timeout: float) -> tuple[Any, float]:
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

    if "application/json" in content_type:
        try:
            return json.loads(raw.decode("utf-8")), latency_ms
        except json.JSONDecodeError as exc:
            raise HfEndpointError(f"HF endpoint returned invalid JSON: {exc}") from exc
    return raw, latency_ms


def decode_audio_payload(payload: Any) -> bytes:
    if isinstance(payload, bytes):
        return payload
    if isinstance(payload, str):
        return base64.b64decode(payload)
    if not isinstance(payload, dict):
        raise HfEndpointError(f"Unsupported audio payload type: {type(payload).__name__}")

    for key in ("audio", "audio_base64", "wav", "wav_base64", "data"):
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return base64.b64decode(value)
        if isinstance(value, bytes):
            return value

    raise HfEndpointError("HF endpoint response did not contain audio bytes")
