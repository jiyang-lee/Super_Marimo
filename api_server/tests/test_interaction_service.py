from __future__ import annotations

import asyncio
import sys
from datetime import datetime, timezone
from types import SimpleNamespace
from pathlib import Path
from uuid import uuid4

CURRENT_DIR = Path(__file__).resolve().parents[1]
LLM_SERVER_DIR = CURRENT_DIR.parent / "llm_server"
sys.path = [entry for entry in sys.path if Path(entry).resolve() != LLM_SERVER_DIR.resolve()]
if str(CURRENT_DIR) not in sys.path:
    sys.path.insert(0, str(CURRENT_DIR))

_ORIGINAL_CONFIG = sys.modules.get("config")
sys.modules.pop("config", None)

import services.interaction_service as service

if _ORIGINAL_CONFIG is None:
    sys.modules.pop("config", None)
else:
    sys.modules["config"] = _ORIGINAL_CONFIG


class _DummyConn:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def cursor(self):
        return _DummyCursor()

    def commit(self):
        return None


class _DummyCursor:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def execute(self, sql, params):
        self.sql = sql
        self.params = params

    def fetchone(self):
        return {"interaction_id": 1, "created_at": datetime(2026, 1, 1, tzinfo=timezone.utc)}


def _patch_common_flow(monkeypatch, runtime_state):
    captured_request: dict[str, object] = {}
    captured_session_meta: list[dict[str, object]] = []

    monkeypatch.setattr(service, "get_db_connection", lambda: _DummyConn())
    monkeypatch.setattr(
        service,
        "load_latest_sensor_payload",
        lambda: SimpleNamespace(
            distance=49.0,
            light=501.0,
            water_level=61.0,
            temperature=27.0,
            humidity=57.0,
            water_level_recent_avg_2h=61.0,
            water_level_normalized_0_100=61,
            water_level_sample_count=3,
            light_daytime_avg_13_18=501.0,
            light_normalized_0_100=72,
            light_daytime_sample_count=5,
            light_daytime_window_label="13:00~18:00 KST",
            sensor_semantics={"water_level_normalized_0_100": 61, "light_normalized_0_100": 72},
            sensor_summary="current merged summary",
            model_dump=lambda: {
                "distance": 49.0,
                "light": 501.0,
                "water_level": 61.0,
                "temperature": 27.0,
                "humidity": 57.0,
                "water_level_recent_avg_2h": 61.0,
                "water_level_normalized_0_100": 61,
                "water_level_sample_count": 3,
                "light_daytime_avg_13_18": 501.0,
                "light_normalized_0_100": 72,
                "light_daytime_sample_count": 5,
                "light_daytime_window_label": "13:00~18:00 KST",
                "sensor_semantics": {"water_level_normalized_0_100": 61, "light_normalized_0_100": 72},
                "sensor_summary": "current merged summary",
            },
        ),
    )
    monkeypatch.setattr(service, "judge_sensor_state", lambda sensor: {"level": "warning", "alerts": ["close"]})
    monkeypatch.setattr(service, "get_runtime_settings", lambda conn=None: dict(runtime_state))
    monkeypatch.setattr(
        service,
        "ensure_session",
        lambda conn, session_id, session_kind=None: (
            {
                "session_id": session_id,
                "created_at": None,
                "last_seen_at": None,
                "ended_at": None,
                "turn_count": 0,
                "meta": {},
            },
            True,
        ),
    )
    monkeypatch.setattr(service, "fetch_recent_session_messages", lambda conn, session_id: [{"role": "user", "content": "최근 대화"}])

    def fake_save_session_message(*args, **kwargs):
        return {"message_id": 1, "created_at": None}

    monkeypatch.setattr(service, "save_session_message", fake_save_session_message)

    def fake_update_session_meta(conn, session_id, patch):
        captured_session_meta.append(patch)
        return {
            "session_id": session_id,
            "created_at": None,
            "last_seen_at": None,
            "ended_at": None,
            "turn_count": 1,
            "meta": patch,
        }

    monkeypatch.setattr(service, "update_session_meta", fake_update_session_meta)
    monkeypatch.setattr(service, "update_session_turn", lambda conn, session_id: {"session_id": session_id, "turn_count": 1, "meta": {}})

    def fake_apply_runtime_action(action, conn=None):
        runtime_state.update(action["patch"])
        return {
            "action_type": action["action_type"],
            "summary": action["summary"],
            "patch": action["patch"],
            "before": action.get("before"),
            "after": {"settings": dict(runtime_state)},
        }

    monkeypatch.setattr(service, "apply_runtime_action", fake_apply_runtime_action)

    return captured_request, captured_session_meta


def test_handle_interaction_uses_llm_action_proposal(monkeypatch) -> None:
    runtime_state = {
        "distance_detection_enabled": True,
        "wake_enabled": True,
        "web_voice_enabled": False,
        "distance_threshold_cm": 50.0,
        "distance_inside_threshold": False,
    }
    captured_request, captured_session_meta = _patch_common_flow(monkeypatch, runtime_state)

    async def fake_request_llm(
        question,
        sensor,
        state,
        runtime_settings,
        use_sensor_context,
        history=None,
        session_summary=None,
        action_result=None,
        persona_memo=None,
        system_memo=None,
    ):
        captured_request.update(
            {
                "question": question,
                "runtime_settings": runtime_settings,
                "use_sensor_context": use_sensor_context,
                "history": history,
                "session_summary": session_summary,
                "action_result": action_result,
                "state": state,
            }
        )
        return {
            "answer": "알겠어요. 설정을 바꿀게요.",
            "action_proposal": {
                "action_type": "update_runtime_settings",
                "patch": {"wake_enabled": False},
                "summary": "깨우기 기능을 껐어요.",
            },
            "confidence": 0.9,
            "reason": "질문 의도가 명확합니다.",
        }

    monkeypatch.setattr(service, "request_llm", fake_request_llm)

    result = asyncio.run(
        service.handle_interaction(
            session_id=uuid4(),
            session_kind="chat",
            text="wake off",
            sensor=None,
            use_sensor_context=True,
            source="ask",
        )
    )

    assert result["action_result"]["summary"] == "깨우기 기능을 껐어요."
    assert result["runtime_settings"]["wake_enabled"] is False
    assert result["llm"]["action_result"]["summary"] == "깨우기 기능을 껐어요."
    assert result["llm"]["final_answer"] == "깨우기 기능을 껐어요. 필요하면 다시 켜주세요!"
    assert captured_request["runtime_settings"]["wake_enabled"] is True
    assert captured_request["use_sensor_context"] is True
    assert captured_session_meta[-1]["last_agent_action"]["summary"] == "깨우기 기능을 껐어요."
    assert captured_session_meta[-1]["last_llm_contract"]["executed_action"]["patch"]["wake_enabled"] is False


def test_handle_interaction_strips_json_wrapper_from_tts_text(monkeypatch) -> None:
    runtime_state = {
        "distance_detection_enabled": True,
        "wake_enabled": True,
        "web_voice_enabled": False,
        "distance_threshold_cm": 50.0,
        "distance_inside_threshold": False,
    }
    _patch_common_flow(monkeypatch, runtime_state)

    async def fake_request_llm(
        question,
        sensor,
        state,
        runtime_settings,
        use_sensor_context,
        history=None,
        session_summary=None,
        action_result=None,
        persona_memo=None,
        system_memo=None,
    ):
        return {
            "answer": '{"answer":"안녕하세요."}',
            "action_proposal": None,
            "confidence": 0.3,
            "reason": "no proposal",
        }

    monkeypatch.setattr(service, "request_llm", fake_request_llm)

    result = asyncio.run(
        service.handle_interaction(
            session_id=uuid4(),
            session_kind="chat",
            text="hello",
            sensor=None,
            use_sensor_context=True,
            source="ask",
        )
    )

    assert result["llm_answer"] == "안녕하세요."
    assert result["tts_text"] == "안녕하세요."


def test_handle_interaction_extracts_answer_from_malformed_json_like_text(monkeypatch) -> None:
    runtime_state = {
        "distance_detection_enabled": True,
        "wake_enabled": True,
        "web_voice_enabled": False,
        "distance_threshold_cm": 50.0,
        "distance_inside_threshold": False,
    }
    _patch_common_flow(monkeypatch, runtime_state)

    async def fake_request_llm(
        question,
        sensor,
        state,
        runtime_settings,
        use_sensor_context,
        history=None,
        session_summary=None,
        action_result=None,
        persona_memo=None,
        system_memo=None,
    ):
        return {
            "answer": '{"answer":"안녕하세요.","action_proposal":null,"confidence":0.85',
            "action_proposal": None,
            "confidence": 0.3,
            "reason": "no proposal",
        }

    monkeypatch.setattr(service, "request_llm", fake_request_llm)

    result = asyncio.run(
        service.handle_interaction(
            session_id=uuid4(),
            session_kind="chat",
            text="hello",
            sensor=None,
            use_sensor_context=True,
            source="ask",
        )
    )

    assert result["llm_answer"] == "안녕하세요."
    assert result["tts_text"] == "안녕하세요."


def test_handle_interaction_falls_back_to_text_resolution(monkeypatch) -> None:
    runtime_state = {
        "distance_detection_enabled": True,
        "wake_enabled": True,
        "web_voice_enabled": False,
        "distance_threshold_cm": 50.0,
        "distance_inside_threshold": False,
    }
    captured_request, captured_session_meta = _patch_common_flow(monkeypatch, runtime_state)

    async def fake_request_llm(
        question,
        sensor,
        state,
        runtime_settings,
        use_sensor_context,
        history=None,
        session_summary=None,
        action_result=None,
        persona_memo=None,
        system_memo=None,
    ):
        captured_request.update(
            {
                "question": question,
                "runtime_settings": runtime_settings,
                "use_sensor_context": use_sensor_context,
                "history": history,
                "session_summary": session_summary,
                "action_result": action_result,
                "state": state,
            }
        )
        return {
            "answer": "알겠어요.",
            "action_proposal": None,
            "confidence": 0.3,
            "reason": "no proposal",
        }

    monkeypatch.setattr(service, "request_llm", fake_request_llm)

    result = asyncio.run(
        service.handle_interaction(
            session_id=uuid4(),
            session_kind="chat",
            text="distance detection off",
            sensor=None,
            use_sensor_context=True,
            source="ask",
        )
    )

    assert result["action_result"]["summary"] == "distance_detection_enabled -> off"
    assert result["runtime_settings"]["distance_detection_enabled"] is False
    assert result["llm"]["final_answer"] == "거리 감지 모드를 껐어요. 필요하면 다시 켜주세요!"
    assert captured_request["runtime_settings"]["distance_detection_enabled"] is True
    assert captured_session_meta[-1]["last_agent_action"]["summary"] == "distance_detection_enabled -> off"



def test_handle_interaction_merges_latest_normalized_sensor_fields(monkeypatch) -> None:
    runtime_state = {
        "distance_detection_enabled": True,
        "wake_enabled": True,
        "web_voice_enabled": False,
        "distance_threshold_cm": 50.0,
        "distance_inside_threshold": False,
    }
    captured_request, _ = _patch_common_flow(monkeypatch, runtime_state)
    captured_sensor: dict[str, object] = {}

    async def fake_request_llm(
        question,
        sensor,
        state,
        runtime_settings,
        use_sensor_context,
        history=None,
        session_summary=None,
        action_result=None,
        persona_memo=None,
        system_memo=None,
    ):
        captured_sensor.update(sensor.model_dump() if sensor is not None else {})
        captured_request.update(
            {
                "question": question,
                "runtime_settings": runtime_settings,
                "use_sensor_context": use_sensor_context,
            }
        )
        return {
            "answer": "ok",
            "action_proposal": None,
            "confidence": 0.3,
            "reason": "no proposal",
        }

    monkeypatch.setattr(service, "request_llm", fake_request_llm)
    monkeypatch.setattr(service, "save_runtime_settings_history", lambda *args, **kwargs: None)

    result = asyncio.run(
        service.handle_interaction(
            session_id=uuid4(),
            session_kind="chat",
            text="??",
            sensor=SimpleNamespace(
                temperature=27.0,
                humidity=57.0,
                light=765.0,
                water_level=199.0,
                distance=49.0,
                model_dump=lambda: {
                    "temperature": 27.0,
                    "humidity": 57.0,
                    "light": 765.0,
                    "water_level": 199.0,
                    "distance": 49.0,
                },
            ),
            use_sensor_context=True,
            source="ask",
        )
    )

    assert result["llm_answer"] == "ok"
    assert result["sensor"]["water_level_normalized_0_100"] == 61
    assert result["sensor"]["light_normalized_0_100"] == 72
    assert captured_sensor["water_level_normalized_0_100"] == 61
    assert captured_sensor["light_normalized_0_100"] == 72
    assert captured_sensor["water_level_recent_avg_2h"] == 61.0
    assert captured_sensor["light_daytime_avg_13_18"] == 501.0
    assert captured_request["use_sensor_context"] is True
