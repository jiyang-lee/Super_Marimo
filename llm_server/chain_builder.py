from typing import Any

from config import MOCK_MODE, logger


def build_mock_answer(payload: Any) -> str:
    if not getattr(payload, "use_sensor_context", False):
        return "좋아. 조금만 더 자세히 말해줘."

    sensor = getattr(payload, "sensor", None) or {}
    state = getattr(payload, "state", None) or {}
    alerts = state.get("alerts") or []
    level = state.get("level", "normal")

    values = []
    for key, label in (
        ("temperature", "기온"),
        ("humidity", "습도"),
        ("light", "조도"),
        ("water_level", "수위"),
        ("distance", "거리"),
    ):
        if sensor.get(key) is not None:
            values.append(f"{label} {sensor[key]}")

    summary = ", ".join(values) if values else "센서 값이 아직 들어오지 않았어요."
    if alerts:
        return f"지금 상태는 {level}예요. {summary}. {', '.join(alerts)}가 보여요."
    return f"지금 상태는 {level}예요. {summary}. 비교적 안정적이에요."


def get_chain():
    from langchain_core.output_parsers import StrOutputParser
    from langchain_core.runnables import RunnableLambda

    if MOCK_MODE:
        model = RunnableLambda(lambda values: build_mock_answer(values["payload"]))
        return RunnableLambda(lambda payload: {"payload": payload}) | model | StrOutputParser()

    from model_engine import generate_answer
    return RunnableLambda(generate_answer) | StrOutputParser()
