from unittest.mock import Base
from datetime import datetime
from pydantic import BaseModel, Field
from typing import Dict, Optional, Any, List
from pydantic import ConfigDict

class UserLogin(BaseModel):
    username: str
    password: str

class UserRegister(BaseModel):
    username: str = Field(min_length=3, max_length=100)
    password: str = Field(min_length=8)

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"

class BackupRequest(BaseModel):
    password: str

class ActionResponse(BaseModel):
    ok: bool
    detail: str

class StatusResponse(BaseModel):
    services: List[Dict[str, Any]]


class MqttConfigDto(BaseModel):
    model_config = ConfigDict(extra="forbid")

    host: str
    port: int = Field(ge=1, le=65535)
    tenant_id: str
    client_id: str
    events_to_handle: Optional[Dict[str, bool]] = None
    integrationId: Optional[str] = None


class SshConfigDto(BaseModel):
    model_config = ConfigDict(extra="forbid")

    host: str
    port: int = Field(ge=1, le=65535)


class HttpClientConfigDto(BaseModel):
    model_config = ConfigDict(extra="forbid")

    http_base_url: Optional[str] = None
    timeout: Optional[float] = None
    verify_ssl: Optional[bool] = None

class ServiceConfigDto(BaseModel):
    model_config = ConfigDict(extra="forbid")

    run_services_on_startup: Optional[bool] = False

class RoomDto(BaseModel):
    id: int
    room_name: str
    ascom_device_id: str

class addRoomDto(BaseModel):
    room_name: str
    ascom_device_id: str

class EventDto(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    room_name: str
    status: str
    created_at: datetime
    updated_at: datetime
    qumea_roomId: Optional[str] = None
    qumea_alertType: Optional[str] = None
    qumea_activeAlertId: str
    



