from typing import Any, Literal, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class SensorPayload(BaseModel):
    temperature: float = Field(..., description="Temperature")
    humidity: float = Field(..., description="Humidity")
    light: float = Field(..., description="Light level")
    water_level: float = Field(..., description="Water level")
    distance: float = Field(..., description="Distance in cm")


class RealtimeSensorPayload(BaseModel):
    temperature: Optional[float] = Field(None, description="Temperature")
    humidity: Optional[float] = Field(None, description="Humidity")
    light: float = Field(..., description="Light level")
    distance: float = Field(..., description="Distance in cm")
    water_level: Optional[float] = Field(None, description="Water level")
    session_id: Optional[str] = Field(None, description="Active session ID if known")
    device_id: str = Field("", description="Device identifier")




class HourlySensorPayload(BaseModel):
    temperature: float = Field(..., description="Temperature")
    humidity: float = Field(..., description="Humidity")
    water_level: float = Field(..., description="Water level")


class RuntimeSettingsPayload(BaseModel):
    distance_detection_enabled: Optional[bool] = None
    wake_enabled: Optional[bool] = None
    web_voice_enabled: Optional[bool] = None
    distance_threshold_cm: Optional[float] = None
    distance_inside_threshold: Optional[bool] = None


class AskPayload(BaseModel):
    question: str
    sensor: Optional[SensorPayload] = None
    session_id: Optional[UUID] = None
    session_kind: Optional[Literal["chat", "voice"]] = None
    use_sensor_context: bool = True
    persona_memo: Optional[str] = None
    system_memo: Optional[str] = None
    is_test: Optional[bool] = None


class VoiceAskPayload(BaseModel):
    text: str
    sensor: Optional[SensorPayload] = None
    session_id: Optional[UUID] = None
    session_kind: Optional[Literal["chat", "voice"]] = "voice"
    use_sensor_context: bool = True
    persona_memo: Optional[str] = None
    system_memo: Optional[str] = None


class DeviceEventBasePayload(BaseModel):
    session_id: Optional[UUID] = None
    device_id: str = Field("", description="Device identifier")
    trigger_source: str = Field("manual", description="Event trigger source")
    distance: Optional[float] = Field(None, description="Distance in cm")
    sensor: Optional[SensorPayload] = None
    state_level: str = "normal"
    state_alerts: list[str] = Field(default_factory=list)
    generated_text: str = Field("", description="Generated event text")
    played: bool = Field(False, description="Whether TTS was played")
    status: str = Field("pending", description="Event lifecycle status")
    meta: dict[str, Any] = Field(default_factory=dict)


class WakewordEventPayload(DeviceEventBasePayload):
    event_type: Literal["wakeword"] = "wakeword"


class ManualTestEventPayload(DeviceEventBasePayload):
    event_type: Literal["manual_test"] = "manual_test"


class DeviceEventPayload(DeviceEventBasePayload):
    event_type: str = Field(..., description="Device event type")
