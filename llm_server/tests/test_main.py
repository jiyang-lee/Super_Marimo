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


class _RunnableBranch:
    def __init__(self, *branches):
        self.branches = branches

    def invoke(self, value):
        for branch in self.branches[:-1]:
            predicate, runnable = branch
            if predicate(value):
                return runnable.invoke(value)
        default_runnable = self.branches[-1]
        return default_runnable.invoke(value)


langchain_runnables = types.ModuleType("langchain_core.runnables")
langchain_runnables.RunnableLambda = _RunnableLambda
langchain_runnables.RunnableBranch = _RunnableBranch
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

if str(CURRENT_DIR) in sys.path:
    sys.path.remove(str(CURRENT_DIR))


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

    assert "JSON 객체만" in prompt
    assert "action_proposal" in prompt
    assert "wake_enabled" in prompt
    assert "custom persona memo" in prompt
    assert "custom system memo" in prompt
    assert "거리 센서는" in prompt
    assert "조도는 화면용 정규화보다 실제 측정값을 우선" in prompt


def test_build_mock_contract_routes_greeting_variations() -> None:
    cases = {
        "안녕 마리모": "안녕. 어떤 걸 확인해볼까요.",
        "안녕하세요 마리모": "안녕하세요. 무엇을 도와드릴까요.",
        "반가워 마리모": "반가워요. 지금 상태를 볼까요.",
    }

    for question, expected in cases.items():
        payload = SimpleNamespace(
            question=question,
            use_sensor_context=True,
            sensor={"temperature": 23.5, "humidity": 55, "distance": 120, "light": 14.0},
            state={"alerts": ["door_open"], "level": "warning"},
            sensor_summary="현재 센서 상태는 warning입니다. 기온 23.5도 / 습도 55.0퍼센트 / 수위 88.0퍼센트 / 조도 14.0럭스.",
        )

        contract = chain_builder.build_mock_contract(payload)

        assert contract["action_proposal"] is None
        assert contract["reason"] == "greeting"
        assert contract["answer"] == expected


def test_build_mock_contract_routes_weather_question() -> None:
    payload = SimpleNamespace(
        question="오늘 날씨 어때",
        use_sensor_context=True,
        sensor={"temperature": 28.0, "humidity": 57.0, "distance": 120.0, "light": 14.0},
        state={"level": "normal"},
        sensor_summary="현재 센서 상태는 normal입니다.",
    )

    contract = chain_builder.build_mock_contract(payload)

    assert contract["action_proposal"] is None
    assert contract["reason"] == "weather_query_declined"
    assert "현재 센서만으로는 오늘 날씨를 알 수 없습니다." in contract["answer"]
    assert "28.0도" in contract["answer"]
    assert "57.0퍼센트" in contract["answer"]


def test_build_mock_contract_routes_distance_question() -> None:
    payload = SimpleNamespace(
        question="거리 센서는 왜 켜져 있어",
        use_sensor_context=True,
        sensor={"distance": 42.0, "temperature": 24.0, "humidity": 50.0},
        runtime_settings={
            "distance_detection_enabled": True,
            "wake_enabled": True,
            "distance_threshold_cm": 50.0,
            "distance_inside_threshold": False,
        },
        state={"level": "normal"},
    )

    contract = chain_builder.build_mock_contract(payload)

    assert contract["action_proposal"] is None
    assert contract["reason"] == "distance_context"
    assert "거리 센서는 환경 대화 모드의 거리 감지와 호출어 허용에만 사용됩니다." in contract["answer"]
    assert "42.0센티미터" in contract["answer"]
    assert "안전" not in contract["answer"]
    assert "위험" not in contract["answer"]


def test_build_mock_contract_routes_sensor_risk_question() -> None:
    payload = SimpleNamespace(
        question="지금 상태 어때",
        use_sensor_context=True,
        sensor={
            "temperature": 28.0,
            "humidity": 57.0,
            "distance": 42.0,
            "light": 14.0,
            "water_level": 100.0,
        },
        state={"level": "normal"},
        sensor_summary="현재 센서 상태는 normal입니다. 기온 28.0도 / 습도 57.0퍼센트 / 수위 100.0퍼센트 / 조도 14.0럭스.",
    )

    contract = chain_builder.build_mock_contract(payload)

    assert contract["action_proposal"] is None
    assert contract["reason"] == "sensor_state_summary"
    assert "기온 28.0도" in contract["answer"]
    assert "습도 57.0퍼센트" in contract["answer"]
    assert "수위 100.0퍼센트" in contract["answer"]
    assert "조도 14.0럭스" in contract["answer"]
    assert "거리" not in contract["answer"]


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
                "answer": "안녕하세요.",
                "action_proposal": None,
                "confidence": 0.5,
                "reason": "dummy",
            }

    monkeypatch.setattr(main_module, "get_chain", lambda: _DummyChain())

    payload = main_module.GeneratePayload(question="hello")
    result = main_module.generate(payload)

    assert result["answer"] == "안녕하세요."
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
        '  "answer": "기온 24도이고 지금 상태는 정상입니다.",\n'
        '  "confidence": "high",\n'
        '  "action_proposal": null\n'
        '}\n'
        '```'
    )
    contract = model_engine.parse_contract_text(bad_json_but_has_answer, payload)

    assert "기온 24도" in contract["answer"]
    assert contract["action_proposal"] is None
