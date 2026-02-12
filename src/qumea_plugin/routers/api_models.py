from pydantic import BaseModel, Field
from typing import Dict, Optional, Any, List

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