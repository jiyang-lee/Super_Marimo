from __future__ import annotations

import sys
import types
from importlib import util
from pathlib import Path
from types import SimpleNamespace


CURRENT_DIR = Path(__file__).resolve().parents[1]
if str(CURRENT_DIR) not in sys.path:
    sys.path.insert(0, str(CURRENT_DIR))


class _RunnableLambda:
    def __init__(self, func):
        self.func = func

    def invoke(self, value):
        return self.func(value)

    def __or__(self, other):
        return self


langchain_runnables = types.ModuleType("langchain_core.runnables")
langchain_runnables.RunnableLambda = _RunnableLambda
sys.modules["langchain_core.runnables"] = langchain_runnables

_ORIGINAL_CONFIG = sys.modules.get("config")
sys.modules.pop("config", None)


def _load_module(module_name: str, path: Path):
    spec = util.spec_from_file_location(module_name, path)
    assert spec is not None and spec.loader is not None
    module = util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


try:
    prompt_builder = _load_module("llm_server_prompt_builder", CURRENT_DIR / "prompt_builder.py")
    model_engine = _load_module("llm_server_model_engine", CURRENT_DIR / "model_engine.py")
    chain_builder = _load_module("llm_server_chain_builder", CURRENT_DIR / "chain_builder.py")
    main_module = _load_module("llm_server_main", CURRENT_DIR / "main.py")
finally:
    if _ORIGINAL_CONFIG is None:
        sys.modules.pop("config", None)
    else:
        sys.modules["config"] = _ORIGINAL_CONFIG


def test_build_system_prompt_mentions_json_contract() -> None:
    payload = SimpleNamespace(
        question="wake off",
        history=[],
        sensor=None,
        state=None,
        use_sensor_context=True,
        persona_memo="custom persona memo",
        system_memo="custom system memo",
    )

    prompt = prompt_builder.build_system_prompt(payload)

    assert "JSON 객체 하나만" in prompt
    assert "action_proposal" in prompt
    assert "wake_enabled" in prompt
    assert "custom persona memo" in prompt
    assert "custom system memo" in prompt


def test_build_mock_contract_proposes_runtime_action() -> None:
    payload = SimpleNamespace(
        question="wake off",
        use_sensor_context=True,
        sensor={"temperature": 23.5, "humidity": 55, "distance": 120},
        state={"alerts": ["door_open"], "level": "warning"},
    )

    contract = chain_builder.build_mock_contract(payload)

    assert contract["action_proposal"] is not None
    assert contract["action_proposal"]["patch"]["wake_enabled"] is False
    assert "온도 23.5" in contract["answer"]
    assert "warning" in contract["answer"]
    assert contract["confidence"] >= 0.8


def test_parse_contract_text_rejects_invalid_action_and_falls_back() -> None:
    payload = SimpleNamespace(
        question="status",
        use_sensor_context=True,
        sensor={"temperature": 24.0, "humidity": 50.0, "distance": 42.0},
        state={"level": "normal"},
    )

    contract = model_engine.parse_contract_text(
        '{"answer":"ok","action_proposal":{"action_type":"update_runtime_settings","patch":{"unknown":1}},"confidence":0.9,"reason":"bad"}',
        payload,
    )

    assert contract["action_proposal"] is None
    assert contract["reason"] == "action_proposal_rejected"

    fallback_contract = model_engine.parse_contract_text("not json at all", payload)
    assert fallback_contract["answer"]
    assert fallback_contract["action_proposal"] is None
    assert fallback_contract["confidence"] == 0.2


def test_generate_endpoint_returns_structured_contract(monkeypatch) -> None:
    class _DummyChain:
        def invoke(self, payload):
            return {
                "answer": "알겠어요.",
                "action_proposal": None,
                "confidence": 0.5,
                "reason": "dummy",
            }

    monkeypatch.setattr(main_module, "get_chain", lambda: _DummyChain())

    payload = main_module.GeneratePayload(question="hello")
    result = main_module.generate(payload)

    assert result["answer"] == "알겠어요."
    assert result["action_proposal"] is None
    assert result["framework"] == "langchain"


def test_parse_contract_text_robust_regex_fallback() -> None:
    payload = SimpleNamespace(
        question="status",
        use_sensor_context=True,
        sensor={"temperature": 24.0, "humidity": 50.0, "distance": 42.0},
        state={"level": "normal"},
    )

    bad_json_but_has_answer = (
        'Here is the response in json format:\n'
        '```json\n'
        '{\n'
        '  "answer": "기온 24도이고 아주 괜찮은 상태예요!",\n'
        '  "confidence": "high",\n'
        '  "action_proposal": None\n'
        '}\n'
        '```'
    )
    contract = model_engine.parse_contract_text(bad_json_but_has_answer, payload)
    assert "기온 24도이고 아주 괜찮은 상태예요!" in contract["answer"]
    assert contract["action_proposal"] is None
