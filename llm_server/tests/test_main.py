import sys
import types
from importlib import util
from pathlib import Path
from types import SimpleNamespace


CURRENT_DIR = Path(__file__).resolve().parents[1]
if str(CURRENT_DIR) not in sys.path:
    sys.path.insert(0, str(CURRENT_DIR))


_ORIGINAL_CONFIG = sys.modules.get("config")
_ORIGINAL_LANGCHAIN = {
    name: sys.modules.get(name)
    for name in (
        "langchain_core.output_parsers",
        "langchain_core.runnables",
    )
}


class _StrOutputParser:
    pass


class _RunnableLambda:
    def __init__(self, func):
        self.func = func

    def __or__(self, other):
        return self


langchain_output_parsers = types.ModuleType("langchain_core.output_parsers")
langchain_output_parsers.StrOutputParser = _StrOutputParser
sys.modules["langchain_core.output_parsers"] = langchain_output_parsers

langchain_runnables = types.ModuleType("langchain_core.runnables")
langchain_runnables.RunnableLambda = _RunnableLambda
sys.modules["langchain_core.runnables"] = langchain_runnables

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
finally:
    if _ORIGINAL_CONFIG is None:
        sys.modules.pop("config", None)
    else:
        sys.modules["config"] = _ORIGINAL_CONFIG

    for name, module in _ORIGINAL_LANGCHAIN.items():
        if module is None:
            sys.modules.pop(name, None)
        else:
            sys.modules[name] = module


def test_build_system_prompt_includes_custom_memos() -> None:
    payload = SimpleNamespace(
        question="안녕",
        history=[],
        sensor=None,
        state=None,
        use_sensor_context=False,
        persona_memo="custom persona memo",
        system_memo="custom system memo",
    )

    prompt = prompt_builder.build_system_prompt(payload)

    assert "custom persona memo" in prompt
    assert "custom system memo" in prompt
    assert "I think" in prompt


def test_build_history_messages_filters_invalid_items() -> None:
    payload = SimpleNamespace(
        history=[
            {"role": "user", "content": "hello"},
            {"role": "assistant", "text": "world"},
            {"role": "system", "content": ""},
            {"role": "robot", "content": "skip"},
        ]
    )

    messages = prompt_builder.build_history_messages(payload)

    assert messages == [
        {"role": "user", "content": "hello"},
        {"role": "assistant", "content": "world"},
    ]


def test_normalize_answer_strips_controls_and_collapses_whitespace() -> None:
    answer = "  hello\u200b world\n\twith\u0000noise  "

    normalized = model_engine.normalize_answer(answer)

    assert normalized == "hello worldwithnoise"


def test_build_mock_answer_uses_sensor_context() -> None:
    payload = SimpleNamespace(
        use_sensor_context=True,
        sensor={"temperature": 23.5, "humidity": 55, "distance": 120},
        state={"alerts": ["door_open"], "level": "warning"},
    )

    answer = chain_builder.build_mock_answer(payload)

    assert "23.5" in answer
    assert "55" in answer
    assert "120" in answer
    assert "door_open" in answer
    assert "warning" in answer


def test_build_mock_answer_without_sensor_context_returns_fallback() -> None:
    payload = SimpleNamespace(use_sensor_context=False)

    answer = chain_builder.build_mock_answer(payload)

    assert isinstance(answer, str)
    assert answer.strip()
