from __future__ import annotations

import json
import re
import unicodedata
from threading import Lock
from typing import Any, Optional

from config import (
    HF_LLM_BACKEND,
    HF_LLM_ENDPOINT_URL,
    HF_LLM_ROUTER_BASE_URL,
    HF_LLM_ROUTER_MODEL,
    HF_TIMEOUT_SEC,
    HF_TOKEN,
    LLM_MODEL_ID,
    LLM_MODEL_REVISION,
    logger,
)
from contracts import build_contract, coerce_contract
from hf_endpoint_client import HF_LLM_RUNTIME_STATE, chat_completion, extract_text, post_json

_MODEL_BUNDLE: Optional[dict[str, Any]] = None
_MODEL_LOCK = Lock()


def normalize_answer(answer: str) -> str:
    cleaned = unicodedata.normalize("NFKC", answer or "")
    cleaned = cleaned.replace("\r\n", "\n").replace("\r", "\n")
    cleaned = re.sub(r"[\u200b-\u200d\ufeff\ufe0e\ufe0f]", "", cleaned)
    cleaned = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", cleaned)
    cleaned = re.sub(r"[ \t]+", " ", cleaned)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned.strip()


def get_model_bundle() -> dict[str, Any]:
    from transformers.models.auto.modeling_auto import AutoModelForCausalLM
    from transformers.models.auto.tokenization_auto import AutoTokenizer
    import torch

    global _MODEL_BUNDLE
    with _MODEL_LOCK:
        if _MODEL_BUNDLE is not None:
            return _MODEL_BUNDLE

        tokenizer = AutoTokenizer.from_pretrained(
            LLM_MODEL_ID,
            revision=LLM_MODEL_REVISION,
            trust_remote_code=True,
        )
        model = AutoModelForCausalLM.from_pretrained(
            LLM_MODEL_ID,
            revision=LLM_MODEL_REVISION,
            low_cpu_mem_usage=False,
            trust_remote_code=True,
        )

        from config import RUN_MODE

        device = "cpu" if RUN_MODE == "cpu" else ("cuda" if torch.cuda.is_available() else "cpu")
        if device == "cuda":
            model = model.half()
        model = model.to(device)
        model.eval()

        _MODEL_BUNDLE = {"tokenizer": tokenizer, "model": model, "device": device}
        return _MODEL_BUNDLE


def get_readiness_state() -> dict[str, Any]:
    from config import MOCK_MODE

    if MOCK_MODE:
        return {
            "ok": True,
            "ready": True,
            "mode": "mock",
            "model_loaded": True,
            "cuda_available": False,
            "device": "mock",
            "error": None,
            "error_type": None,
        }

    try:
        import torch

        if HF_LLM_BACKEND == "router" and HF_TOKEN:
            return {
                "ok": True,
                "ready": True,
                "mode": "hf_router",
                "model_loaded": True,
                "cuda_available": torch.cuda.is_available(),
                "device": "hf_router",
                "error": HF_LLM_RUNTIME_STATE.get("last_error"),
                "error_type": None,
                "last_latency_ms": HF_LLM_RUNTIME_STATE.get("last_latency_ms"),
            }

        if HF_LLM_ENDPOINT_URL:
            return {
                "ok": True,
                "ready": True,
                "mode": "hf_endpoint",
                "model_loaded": True,
                "cuda_available": torch.cuda.is_available(),
                "device": "hf_endpoint",
                "error": HF_LLM_RUNTIME_STATE.get("last_error"),
                "error_type": None,
                "last_latency_ms": HF_LLM_RUNTIME_STATE.get("last_latency_ms"),
            }

        bundle = get_model_bundle()
        return {
            "ok": True,
            "ready": True,
            "mode": "huggingface",
            "model_loaded": True,
            "cuda_available": torch.cuda.is_available(),
            "device": bundle["device"],
            "error": None,
            "error_type": None,
        }
    except Exception as exc:
        logger.exception("LLM readiness check failed: %s", exc)
        return {
            "ok": False,
            "ready": False,
            "mode": "huggingface",
            "model_loaded": False,
            "cuda_available": False,
            "device": None,
            "error": str(exc),
            "error_type": exc.__class__.__name__,
        }


def _safe_plain_text(payload: Any) -> str:
    sensor = getattr(payload, "sensor", None) or {}
    state = getattr(payload, "state", None) or {}
    runtime_settings = getattr(payload, "runtime_settings", None) or {}
    if hasattr(sensor, "model_dump"):
        sensor = sensor.model_dump()
    if hasattr(state, "model_dump"):
        state = state.model_dump()
    if hasattr(runtime_settings, "model_dump"):
        runtime_settings = runtime_settings.model_dump()

    question = str(getattr(payload, "question", "") or "").strip().lower()
    distance_keywords = ("거리", "distance", "가까워", "멀어", "threshold", "near", "far", "근접")
    is_distance_question = any(keyword in question for keyword in distance_keywords)

    def _num(key: str) -> float | None:
        try:
            value = sensor.get(key) if isinstance(sensor, dict) else None
            return None if value is None else float(value)
        except (TypeError, ValueError):
            return None

    def _first_num(*keys: str) -> float | None:
        for key in keys:
            value = _num(key)
            if value is not None:
                return value
        return None

    if is_distance_question:
        distance = _num("distance")
        threshold = runtime_settings.get("distance_threshold_cm") if isinstance(runtime_settings, dict) else None
        inside = runtime_settings.get("distance_inside_threshold") if isinstance(runtime_settings, dict) else None
        parts = ["어떻게 거리 기준을 알실까요"]
        if distance is not None:
            parts.append(f"현재 거리는 {distance:.1f}cm입니다.")
        if threshold is not None:
            try:
                parts.append(f"기준은 {float(threshold):.0f}cm입니다.")
            except (TypeError, ValueError):
                pass
        if inside is True:
            parts.append("지금은 기준 안쪽입니다.")
        elif inside is False:
            parts.append("지금은 기준 바깜쪽입니다.")
        return " ".join(parts)

    temperature = _num("temperature")
    humidity = _num("humidity")
    water_level = _first_num("water_level_normalized_0_100", "water_level_recent_avg_2h", "water_level")
    light = _first_num("light_normalized_0_100", "light_daytime_avg_13_18", "light")
    state_level = str(state.get("level") or "normal").strip() or "normal"
    state_level_kr = {"normal": "정상", "warning": "주의", "critical": "위험"}.get(state_level, state_level)

    parts = [f"현재 상태는 {state_level_kr}입니다."]
    if temperature is not None:
        parts.append(f"기온 {temperature:.1f}도")
    if humidity is not None:
        parts.append(f"습도 {humidity:.1f}%")
    if water_level is not None:
        parts.append(f"수위 {water_level:.1f}%")
    if light is not None:
        parts.append(f"조도 {light:.1f}%")

    if len(parts) == 1:
        return "죄송해요, 다시 말씀해 주실래요?"
    return " / ".join(parts)


def _extract_json_blob(text: str) -> str | None:
    cleaned = normalize_answer(text)
    if not cleaned:
        return None

    cleaned = re.sub(r"```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
    cleaned = cleaned.replace("```", "").strip()

    start = cleaned.find("{")
    if start < 0:
        return None

    depth = 0
    in_string = False
    escape = False
    for index in range(start, len(cleaned)):
        char = cleaned[index]
        if in_string:
            if escape:
                escape = False
            elif char == "\\":
                escape = True
            elif char == '"':
                in_string = False
            continue

        if char == '"':
            in_string = True
            continue
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return cleaned[start : index + 1]
    return None


def _sanitize_action_proposal(action_proposal: Any) -> dict[str, Any] | None:
    if not isinstance(action_proposal, dict):
        return None

    action_type = str(action_proposal.get("action_type") or "").strip()
    if action_type != "update_runtime_settings":
        return None

    patch = action_proposal.get("patch")
    if not isinstance(patch, dict):
        return None

    allowed_keys = {
        "wake_enabled",
        "distance_detection_enabled",
        "distance_threshold_cm",
        "web_voice_enabled",
    }
    sanitized_patch: dict[str, Any] = {}
    for key, value in patch.items():
        if key not in allowed_keys:
            continue
        if key == "distance_threshold_cm":
            try:
                numeric_value = float(value)
            except (TypeError, ValueError):
                continue
            if numeric_value <= 0:
                continue
            sanitized_patch[key] = numeric_value
            continue
        if isinstance(value, bool):
            sanitized_patch[key] = value
            continue
        if isinstance(value, (int, float)):
            sanitized_patch[key] = bool(value)
            continue
        if isinstance(value, str):
            normalized = value.strip().lower()
            if normalized in {"true", "1", "yes", "on"}:
                sanitized_patch[key] = True
            elif normalized in {"false", "0", "no", "off"}:
                sanitized_patch[key] = False

    if not sanitized_patch:
        return None

    summary = normalize_answer(str(action_proposal.get("summary") or "")) or "runtime settings updated"
    return {
        "action_type": "update_runtime_settings",
        "patch": sanitized_patch,
        "summary": summary,
    }


def _build_fallback_contract(payload: Any, *, raw_text: str = "") -> dict[str, Any]:
    answer = normalize_answer(raw_text)
    if not answer:
        answer = _safe_plain_text(payload)

    question = str(getattr(payload, "question", "") or "").strip().lower()
    if question and len(answer) < 60 and any(keyword in question for keyword in ("일반", "안녕", "hello", "hi", "how", "뭐")):
        answer = f"{answer} 조금 더 구체적으로 말해 주면 더 정확하게 답할 수 있습니다."

    return build_contract(
        answer=answer,
        action_proposal=None,
        confidence=0.2,
        reason="json_parse_failed",
    )


def parse_contract_text(text: str, payload: Any | None = None) -> dict[str, Any]:
    blob = _extract_json_blob(text)
    if blob is None:
        return _build_fallback_contract(payload, raw_text=text)

    try:
        raw = json.loads(blob)
    except json.JSONDecodeError:
        return _build_fallback_contract(payload, raw_text=text)

    contract = coerce_contract(raw)
    if contract is None:
        fallback_text = str(raw.get("answer") or "") if isinstance(raw, dict) else ""
        return _build_fallback_contract(payload, raw_text=fallback_text or text)

    contract["answer"] = normalize_answer(str(contract.get("answer") or "")) or _safe_plain_text(payload)
    contract["reason"] = str(contract.get("reason") or "").strip()
    contract["action_proposal"] = _sanitize_action_proposal(contract.get("action_proposal"))
    if contract["action_proposal"] is None and isinstance(raw, dict) and raw.get("action_proposal") is not None:
        contract["reason"] = "action_proposal_rejected"

    confidence = contract.get("confidence")
    try:
        contract["confidence"] = max(0.0, min(float(confidence), 1.0))
    except (TypeError, ValueError):
        contract["confidence"] = 0.0
    return contract


def generate_contract(payload: Any) -> dict[str, Any]:
    from prompt_builder import build_history_messages, build_system_prompt, build_user_prompt

    messages = [{"role": "system", "content": build_system_prompt(payload)}]
    messages.extend(build_history_messages(payload))
    messages.append({"role": "user", "content": build_user_prompt(payload)})
    max_new_tokens = 36 if bool(getattr(payload, "use_sensor_context", False)) else 48

    if HF_LLM_BACKEND == "router" and HF_TOKEN:
        try:
            response, latency_ms = chat_completion(
                base_url=HF_LLM_ROUTER_BASE_URL,
                api_key=HF_TOKEN,
                model=HF_LLM_ROUTER_MODEL,
                messages=messages,
                max_tokens=max_new_tokens,
                timeout=HF_TIMEOUT_SEC,
            )
            HF_LLM_RUNTIME_STATE.update(
                {
                    "ready": True,
                    "backend": "router",
                    "model": HF_LLM_ROUTER_MODEL,
                    "last_latency_ms": latency_ms,
                    "last_error": None,
                }
            )
            text = extract_text(response)
            if not text:
                return _build_fallback_contract(payload, raw_text="")
            return parse_contract_text(text, payload)
        except Exception as exc:
            HF_LLM_RUNTIME_STATE.update({"ready": False, "last_error": str(exc)})
            logger.warning("HF Router LLM failed, trying next LLM backend: %s", exc)

    if HF_LLM_ENDPOINT_URL:
        request_body = {
            "messages": messages,
            "inputs": messages[-1]["content"],
            "parameters": {
                "max_new_tokens": max_new_tokens,
                "temperature": 0.0,
                "do_sample": False,
                "return_full_text": False,
            },
        }
        try:
            response, latency_ms = post_json(HF_LLM_ENDPOINT_URL, request_body, token=HF_TOKEN, timeout=HF_TIMEOUT_SEC)
            HF_LLM_RUNTIME_STATE.update(
                {
                    "ready": True,
                    "backend": "endpoint",
                    "model": LLM_MODEL_ID,
                    "last_latency_ms": latency_ms,
                    "last_error": None,
                }
            )
            text = extract_text(response)
            if not text:
                return _build_fallback_contract(payload, raw_text="")
            return parse_contract_text(text, payload)
        except Exception as exc:
            HF_LLM_RUNTIME_STATE.update({"ready": False, "last_error": str(exc)})
            logger.warning("HF LLM endpoint failed, falling back to local model: %s", exc)

    import torch

    bundle = get_model_bundle()
    tokenizer = bundle["tokenizer"]
    model = bundle["model"]
    device = bundle["device"]

    prompt = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    inputs = tokenizer(prompt, return_tensors="pt").to(device)

    with torch.inference_mode():
        output_ids = model.generate(
            **inputs,
            do_sample=False,
            max_new_tokens=max_new_tokens,
            temperature=0.0,
            top_p=1.0,
        )

    generated_ids = output_ids[0][inputs["input_ids"].shape[-1] :]
    text = tokenizer.decode(generated_ids, skip_special_tokens=True)
    if not text.strip():
        return _build_fallback_contract(payload, raw_text=text)
    return parse_contract_text(text, payload)
