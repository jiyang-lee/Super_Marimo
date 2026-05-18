from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class SensorPayload(BaseModel):
    temperature: float = Field(..., description="섭씨 온도")
    humidity: float = Field(..., description="상대습도 퍼센트")
    light: float = Field(..., description="조도 센서값")
    water_level: float = Field(..., description="수위 센서값")
    distance: float = Field(..., description="초음파 거리 cm")


class RealtimeSensorPayload(BaseModel):
    light: float = Field(..., description="조도 센서값")
    distance: float = Field(..., description="초음파 거리 cm")


class HourlySensorPayload(BaseModel):
    temperature: float = Field(..., description="섭씨 온도")
    humidity: float = Field(..., description="상대습도 퍼센트")
    water_level: float = Field(..., description="수위 센서값")
    water_raw: Optional[int] = Field(None, description="수위 센서 raw ADC 평균값")


class AskPayload(BaseModel):
    question: str
    sensor: SensorPayload
    session_id: Optional[UUID] = None
    use_sensor_context: bool = True


class VoiceAskPayload(BaseModel):
    text: str
    sensor: Optional[SensorPayload] = None
    session_id: Optional[UUID] = None
    use_sensor_context: bool = False


class DeviceEventBasePayload(BaseModel):
    session_id: Optional[UUID] = None
    device_id: str = Field("", description="기기 식별자")
    trigger_source: str = Field("manual", description="이벤트 발생 원인")
    distance: Optional[float] = Field(None, description="이벤트 거리 cm")
    sensor: Optional[SensorPayload] = None
    state_level: str = "normal"
    state_alerts: list[str] = Field(default_factory=list)
    generated_text: str = Field("", description="이벤트와 연결된 생성 텍스트")
    played: bool = Field(False, description="TTS 출력 여부")
    meta: dict[str, Any] = Field(default_factory=dict)


class WakewordEventPayload(DeviceEventBasePayload):
    event_type: str = "wakeword"


class ManualTestEventPayload(DeviceEventBasePayload):
    event_type: str = "manual_test"
