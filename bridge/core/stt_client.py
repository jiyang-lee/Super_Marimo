import json
import mimetypes
import uuid
from typing import Any
from urllib import error as urlerror
from urllib import request as urlrequest


def post_multipart(url: str, field_name: str, filename: str, content: bytes, timeout: int) -> dict:
    boundary = f"----marimo-{uuid.uuid4().hex}"
    mime_type = mimetypes.guess_type(filename)[0] or "application/octet-stream"
    parts = [
        f"--{boundary}\r\n".encode("utf-8"),
        (
            f'Content-Disposition: form-data; name="{field_name}"; filename="{filename}"\r\n'
            f"Content-Type: {mime_type}\r\n\r\n"
        ).encode("utf-8"),
        content,
        b"\r\n",
        f"--{boundary}--\r\n".encode("utf-8"),
    ]
    body = b"".join(parts)
    request = urlrequest.Request(
        url,
        data=body,
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        method="POST",
    )
    try:
        with urlrequest.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except urlerror.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {exc.code} from {url}: {detail}") from exc


class SttClient:
    def __init__(self, endpoint: str, model: str = "fast"):
        self.endpoint = endpoint
        self.model = model

    def transcribe(self, wav_bytes: bytes) -> str:
        url = f"{self.endpoint}?model={self.model}"
        result = post_multipart(url, "audio", "bridge.wav", wav_bytes, timeout=60)
        return (result.get("text") or "").strip()
