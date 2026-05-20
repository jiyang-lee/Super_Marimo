from __future__ import annotations

import json
import re
import unicodedata
from threading import Lock
from typing import Any, Optional

from config import LLM_MODEL_ID, LLM_MODEL_REVISION, logger
from contracts import build_contract, coerce_contract

_MODEL_BUNDLE: Optional[dict[str, Any]] = None
_MODEL_LOCK = Lock()


def normalize_answer(answer: str) -> str:
    cleaned = unicodedata.normalize("NFKC", answer or "")
    cleaned = re.sub(r"[\u200b-\u200d\ufeff\ufe0e\ufe0f]", "", cleaned)
    cleaned = re.sub(r"[\x00-\x1f\x7f]", "", cleaned)
    cleaned = cleaned.replace("\r", "\n")
    cleaned = re.sub(r"[A-Za-z]+", "", cleaned)
    cleaned = re.sub(r"[`\"'“”‘’\[\]{}<>]", "", cleaned)
    cleaned = re.sub(r"[|\\]+", " ", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    if not cleaned:
        return ""
    sentences = [part.strip(" ,;:") for part in re.split(r"(?<=[.!?])\s+|\n+", cleaned) if part.strip(" ,;:")]
    if not sentences:
        return cleaned
    return " ".join(sentences[:3])


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
    distance_keywords = ("거리", "distance", "wake", "호출어", "threshold", "follow-up", "follow up", "호출", "감지")
    is_distance_question = any(keyword in question for keyword in distance_keywords)

    def _num(key: str) -> float | None:
        try:
            value = sensor.get(key) if isinstance(sensor, dict) else None
            return None if value is None else float(value)
        except (TypeError, ValueError):
            return None

    if is_distance_question:
        distance = _num("distance")
        threshold = runtime_settings.get("distance_threshold_cm") if isinstance(runtime_settings, dict) else None
        inside = runtime_settings.get("distance_inside_threshold") if isinstance(runtime_settings, dict) else None
        parts = ["거리 센서는 환경 대화 모드의 거리 감지와 호출어 허용에만 사용됩니다."]
        if distance is not None:
            parts.append(f"현재 거리는 {distance:.1f}센티미터입니다.")
        if threshold is not None:
            try:
                parts.append(f"기준은 {float(threshold):.0f}센티미터입니다.")
            except (TypeError, ValueError):
                pass
        if inside is not None:
            parts.append("현재는 기준 안쪽입니다." if inside else "현재는 기준 바깥쪽입니다.")
        return " ".join(parts)

    temperature = _num("temperature")
    humidity = _num("humidity")
    water_level = _num("water_level")
    if water_level is None:
        water_level = _num("water_level_normalized_0_100")
    light = _num("light")
    if light is None:
        light = _num("light_daytime_avg_13_18")
    state_level = str(state.get("level") or "normal").strip() or "normal"

    parts = [f"현재 센서 상태는 {state_level}입니다."]
    if temperature is not None:
        parts.append(f"기온 {temperature:.1f}도")
    if humidity is not None:
        parts.append(f"습도 {humidity:.1f}퍼센트")
    if water_level is not None:
        parts.append(f"수위 {water_level:.1f}퍼센트")
    if light is not None:
        parts.append(f"조도 {light:.1f}럭스")

    if len(parts) == 1:
        return "현재 센서 값을 바로 읽을 수 없습니다."
    return " / ".join(parts)


def _extract_json_blob(text: str) -> str | None:
    cleaned = (text or "").strip()
    if not cleaned:
        return None

    cleaned = re.sub(r"```(?:json)?\s*", "", cleaned)
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
    question = str(getattr(payload, "question", "") or "").strip()
    if question and len(answer) < 80:
        lowered = question.lower()
        if any(keyword in lowered for keyword in ("wake", "distance", "voice", "threshold", "호출어", "거리")):
            answer = f"{answer} 설정이 필요하면 구체적으로 말씀해 주세요."
    return build_contract(
        answer=answer,
        action_proposal=None,
        confidence=0.2,
        reason="json_parse_failed",
    )


def parse_contract_text(text: str, payload: Any | None = None) -> dict[str, Any]:
    extracted_answer = None

    match = re.search(r'"answer"\s*:\s*"([^"\\]*(?:\\.[^"\\]*)*)"', text, re.DOTALL)
    if match:
        try:
            extracted_answer = json.loads(f'"{match.group(1)}"')
        except Exception:
            extracted_answer = match.group(1)

    if not extracted_answer:
        lazy_match = re.search(r'"answer"\s*:\s*"(.*?)"(?:\s*,|\s*\})', text, re.DOTALL)
        if lazy_match:
            try:
                extracted_answer = json.loads(f'"{lazy_match.group(1)}"')
            except Exception:
                extracted_answer = lazy_match.group(1)

    blob = _extract_json_blob(text)
    if blob is None:
        raw_text = extracted_answer if extracted_answer else text
        return _build_fallback_contract(payload, raw_text=raw_text)

    try:
        raw = json.loads(blob)
    except json.JSONDecodeError:
        raw_text = extracted_answer if extracted_answer else text
        return _build_fallback_contract(payload, raw_text=raw_text)

    contract = coerce_contract(raw)
    if contract is None:
        fallback_text = str(raw.get("answer") or "") if isinstance(raw, dict) else ""
        if not fallback_text and extracted_answer:
            fallback_text = extracted_answer
        return _build_fallback_contract(payload, raw_text=fallback_text or text)

    contract["answer"] = normalize_answer(str(contract.get("answer") or "")) or _safe_plain_text(payload)
    if not contract["answer"] and extracted_answer:
        contract["answer"] = normalize_answer(extracted_answer)

    contract["reason"] = str(contract.get("reason") or "").strip()
    contract["action_proposal"] = _sanitize_action_proposal(contract.get("action_proposal"))
    if contract["action_proposal"] is None and raw.get("action_proposal") is not None:
        contract["reason"] = "action_proposal_rejected"
    confidence = contract.get("confidence")
    try:
        contract["confidence"] = max(0.0, min(float(confidence), 1.0))
    except (TypeError, ValueError):
        contract["confidence"] = 0.0
    return contract


def generate_contract(payload: Any) -> dict[str, Any]:
    import torch

    from prompt_builder import build_history_messages, build_system_prompt, build_user_prompt

    bundle = get_model_bundle()
    tokenizer = bundle["tokenizer"]
    model = bundle["model"]
    device = bundle["device"]

    messages = [{"role": "system", "content": build_system_prompt(payload)}]
    messages.extend(build_history_messages(payload))
    messages.append({"role": "user", "content": build_user_prompt(payload)})

    prompt = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    inputs = tokenizer(prompt, return_tensors="pt").to(device)

    with torch.inference_mode():
        output_ids = model.generate(
            **inputs,
            do_sample=False,
            max_new_tokens=192,
            temperature=0.0,
            top_p=1.0,
        )

    generated_ids = output_ids[0][inputs["input_ids"].shape[-1] :]
    text = tokenizer.decode(generated_ids, skip_special_tokens=True)
    if not text.strip():
        return _build_fallback_contract(payload, raw_text=text)
    return parse_contract_text(text, payload)
