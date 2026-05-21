from __future__ import annotations

import sys
from importlib import util
from pathlib import Path
from types import SimpleNamespace


CURRENT_DIR = Path(__file__).resolve().parents[1]
sys.path = [entry for entry in sys.path if Path(entry).resolve() != CURRENT_DIR.resolve()]
sys.path.insert(0, str(CURRENT_DIR))

_ORIGINAL_CONFIG = sys.modules.get("config")
for _module_name in ("config", "chain_builder", "model_engine", "prompt_builder", "main"):
    sys.modules.pop(_module_name, None)


def _load_module(module_name: str, path: Path):
    spec = util.spec_from_file_location(module_name, path)
    assert spec is not None and spec.loader is not None
    module = util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


try:
    prompt_builder = _load_module("llm_server_prompt_builder", CURRENT_DIR / "prompt_builder.py")
    model_engine = _load_module("llm_server_model_engine", CURRENT_DIR / "model_engine.py")
    chain_builder = _load_module("llm_server_chain_builder", CURRENT_DIR / "chain_builder.py")
    main_module = _load_module("main", CURRENT_DIR / "main.py")
finally:
    if _ORIGINAL_CONFIG is None:
        sys.modules.pop("config", None)
    else:
        sys.modules["config"] = _ORIGINAL_CONFIG

if str(CURRENT_DIR) in sys.path:
    sys.path.remove(str(CURRENT_DIR))


def test_build_system_prompt_requests_natural_dialogue() -> None:
    payload = SimpleNamespace(
        question="안녕",
        history=[],
        sensor=None,
        state=None,
        use_sensor_context=True,
        persona_memo="custom persona memo",
        system_memo="custom system memo",
    )

    prompt = prompt_builder.build_system_prompt(payload)

    assert "JSON 객체만 출력한다" in prompt
    assert "일반 대화는 자연스러운 한국어 대화체" in prompt
    assert "인사, 잡담, 설명" in prompt
    assert "action_proposal" in prompt
    assert "wake_enabled" in prompt
    assert "custom persona memo" in prompt
    assert "custom system memo" in prompt


def test_build_user_prompt_omits_distance_context_for_general_dialogue() -> None:
    payload = SimpleNamespace(
        question="오늘 뭐해?",
        history=[],
        sensor={"distance": 42.0, "temperature": 28.0},
        state={"level": "warning"},
        runtime_settings={"distance_threshold_cm": 50.0},
        session_summary="최근 대화 없음",
        action_result=None,
        use_sensor_context=False,
    )

    prompt = prompt_builder.build_user_prompt(payload)

    assert "distance_context" not in prompt
    assert "sensor:" not in prompt
    assert "state:" not in prompt


def test_route_contract_sends_general_dialogue_to_model_without_sensor_context(monkeypatch) -> None:
    captured: dict[str, object] = {}

    def fake_generate_contract(payload):  # noqa: ANN001
        captured["question"] = payload.question
        captured["use_sensor_context"] = payload.use_sensor_context
        captured["history"] = payload.history
        return {"answer": "모델 답변", "action_proposal": None, "confidence": 0.8, "reason": "model"}

    monkeypatch.setattr(chain_builder, "generate_contract", fake_generate_contract)

    payload = SimpleNamespace(
        question="오늘 뭐해?",
        history=[{"role": "user", "content": "hello"}],
        sensor={"distance": 10},
        state={"level": "warning"},
        runtime_settings={"distance_threshold_cm": 50},
        use_sensor_context=True,
    )

    result = chain_builder.route_contract(payload)

    assert result["answer"] == "모델 답변"
    assert captured["question"] == "오늘 뭐해?"
    assert captured["use_sensor_context"] is False
    assert captured["history"] == [{"role": "user", "content": "hello"}]


def test_route_contract_keeps_sensor_questions_on_rule_path() -> None:
    weather = SimpleNamespace(
        question="오늘 날씨 어때?",
        sensor={"temperature": 28.0, "humidity": 57.0},
        state={"level": "normal"},
        runtime_settings={},
        use_sensor_context=True,
    )
    distance = SimpleNamespace(
        question="거리 가까워?",
        sensor={"distance": 42.0},
        state={"level": "normal"},
        runtime_settings={"distance_threshold_cm": 50.0, "distance_inside_threshold": False},
        use_sensor_context=True,
    )
    risk = SimpleNamespace(
        question="지금 상태 어때?",
        sensor={"temperature": 28.0, "humidity": 57.0, "light": 14.0},
        state={"level": "warning"},
        runtime_settings={},
        use_sensor_context=True,
    )

    weather_contract = chain_builder.route_contract(weather)
    distance_contract = chain_builder.route_contract(distance)
    risk_contract = chain_builder.route_contract(risk)

    assert weather_contract["reason"] == "weather_question"
    assert distance_contract["reason"] == "distance_question"
    assert risk_contract["reason"] == "sensor_state_summary"


def test_route_contract_sends_setting_intent_to_model(monkeypatch) -> None:
    captured: dict[str, object] = {}

    def fake_generate_contract(payload):  # noqa: ANN001
        captured["question"] = payload.question
        captured["use_sensor_context"] = payload.use_sensor_context
        return {"answer": "설정 변경", "action_proposal": None, "confidence": 0.7, "reason": "model"}

    monkeypatch.setattr(chain_builder, "generate_contract", fake_generate_contract)

    payload = SimpleNamespace(
        question="거리 감지 꺼줘",
        sensor={"distance": 42.0},
        state={"level": "warning"},
        runtime_settings={"distance_threshold_cm": 50.0},
        use_sensor_context=True,
    )

    result = chain_builder.route_contract(payload)

    assert result["answer"] == "설정 변경"
    assert captured["question"] == "거리 감지 꺼줘"
    assert captured["use_sensor_context"] is False


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


def test_normalize_answer_preserves_readable_text() -> None:
    text = model_engine.normalize_answer("Hello, world!\r\n안녕?")

    assert "Hello" in text
    assert "world" in text
    assert "안녕" in text
    assert "!" in text


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
    assert result["framework"] == "python"


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



def test_safe_plain_text_prefers_normalized_sensor_values() -> None:
    payload = SimpleNamespace(
        question="status",
        sensor={
            "temperature": 27.0,
            "humidity": 57.0,
            "water_level": 199.0,
            "water_level_normalized_0_100": 73.0,
            "light": 765.0,
            "light_normalized_0_100": 28.0,
        },
        state={"level": "normal"},
        runtime_settings={},
    )

    text = model_engine._safe_plain_text(payload)

    assert "199.0" not in text
    assert "765.0" not in text
    assert "73.0%" in text
    assert "28.0%" in text



def test_sensor_summary_prefers_normalized_values() -> None:
    payload = SimpleNamespace(
        question="status",
        sensor={
            "temperature": 27.0,
            "humidity": 57.0,
            "water_level": 199.0,
            "water_level_normalized_0_100": 73.0,
            "light": 765.0,
            "light_normalized_0_100": 28.0,
        },
        state={"level": "normal"},
    )

    text = chain_builder._sensor_summary(payload)

    assert "199.0" not in text
    assert "765.0" not in text
    assert "73.0%" in text
    assert "28.0%" in text
