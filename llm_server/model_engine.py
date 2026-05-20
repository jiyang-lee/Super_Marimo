import logging
import re
import unicodedata
from threading import Lock
from typing import Any, Optional

from config import LLM_MODEL_ID, LLM_MODEL_REVISION, logger

_MODEL_BUNDLE: Optional[dict[str, Any]] = None
_MODEL_LOCK = Lock()


def normalize_answer(answer: str) -> str:
    cleaned = unicodedata.normalize("NFKC", answer or "")
    cleaned = re.sub(r"[\u200b-\u200d\ufeff\ufe0e\ufe0f]", "", cleaned)
    cleaned = re.sub(r"[\x00-\x1f\x7f]", "", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned)
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


def generate_answer(payload: Any) -> str:
    import torch

    from prompt_builder import build_history_messages, build_system_prompt, format_context

    question = payload.question.strip()
    bundle = get_model_bundle()
    tokenizer = bundle["tokenizer"]
    model = bundle["model"]
    device = bundle["device"]

    messages = [{"role": "system", "content": build_system_prompt(payload)}]
    messages.extend(build_history_messages(payload))
    messages.append(
        {
            "role": "user",
            "content": f"사용자 질문: {question}\n\n참고 정보:\n{format_context(payload)}",
        }
    )

    prompt = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    inputs = tokenizer(prompt, return_tensors="pt").to(device)

    with torch.inference_mode():
        output_ids = model.generate(
            **inputs,
            do_sample=False,
            max_new_tokens=96,
            repetition_penalty=1.12,
            no_repeat_ngram_size=2,
            length_penalty=0.9,
            pad_token_id=tokenizer.eos_token_id,
        )

    generated_ids = output_ids[0][inputs["input_ids"].shape[-1]:]
    return normalize_answer(tokenizer.decode(generated_ids, skip_special_tokens=True))
