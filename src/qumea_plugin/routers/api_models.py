from pydantic import BaseModel, Field
from typing import Dict, Optional, Any, List
from pydantic import ConfigDict

class UserLogin(BaseModel):
    user_name: str
    password: str

class UserRegister(BaseModel):
    user_name: str = Field(min_length=3, max_length=100)
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
    subscribe_topic: str
    keepalive_in_topic: str
    keepalive_out_topic: str


class SshConfigDto(BaseModel):
    model_config = ConfigDict(extra="forbid")

    host: str
    port: int = Field(ge=1, le=65535)
    command: str


class HttpClientConfigDto(BaseModel):
    model_config = ConfigDict(extra="forbid")

    timeout: float = Field(gt=0, default=10.0)
    base_url: Optional[str] = None
    verify_ssl: bool = True
