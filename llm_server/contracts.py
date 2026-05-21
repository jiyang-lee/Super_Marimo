from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, ValidationError


class ActionProposal(BaseModel):
    action_type: Literal["update_runtime_settings"] = "update_runtime_settings"
    patch: dict[str, Any] = Field(default_factory=dict)
    summary: str = ""


class LLMContract(BaseModel):
    answer: str = ""
    action_proposal: ActionProposal | None = None
    confidence: float = 0.0
    reason: str = ""


def coerce_contract(data: Any) -> dict[str, Any] | None:
    if not isinstance(data, dict):
        return None

    try:
        if hasattr(LLMContract, "model_validate"):
            contract = LLMContract.model_validate(data)
        elif hasattr(LLMContract, "parse_obj"):
            contract = LLMContract.parse_obj(data)
        else:
            contract = LLMContract(**data)
    except (TypeError, ValueError, ValidationError):
        return None

    if hasattr(contract, "model_dump"):
        result = contract.model_dump()
    elif hasattr(contract, "dict"):
        result = contract.dict()
    else:
        result = dict(vars(contract))
    action_proposal = result.get("action_proposal")
    if action_proposal is not None and not isinstance(action_proposal, dict):
        result["action_proposal"] = None
    return result


def build_contract(
    *,
    answer: str,
    action_proposal: dict[str, Any] | None,
    confidence: float,
    reason: str,
) -> dict[str, Any]:
    return {
        "answer": str(answer or "").strip(),
        "action_proposal": action_proposal,
        "confidence": max(0.0, min(float(confidence), 1.0)),
        "reason": str(reason or "").strip(),
    }
