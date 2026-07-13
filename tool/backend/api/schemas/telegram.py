from typing import Optional
from pydantic import BaseModel, Field


class UserbotConfigRequest(BaseModel):
    api_id: int
    api_hash: str = Field(min_length=32, max_length=32)
    phone: str = Field(pattern=r"^\+\d{7,15}$")
    session_name: str = "userbot"


class SendCodeRequest(BaseModel):
    phone: str = Field(pattern=r"^\+\d{7,15}$")


class ConfirmCodeRequest(BaseModel):
    phone: str
    code: str = Field(min_length=4, max_length=8)
    phone_code_hash: str


class Confirm2FARequest(BaseModel):
    password: str = Field(min_length=1, max_length=256)


class UserbotStatusOut(BaseModel):
    status: str
    username: Optional[str] = None
    first_name: Optional[str] = None
    phone_masked: Optional[str] = None
    error_msg: Optional[str] = None


class BotTokenRequest(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    token: str = Field(min_length=40, max_length=128)


class BotCredentialOut(BaseModel):
    id: int
    name: str
    username: Optional[str]
    bot_id: Optional[int]
    is_active: bool
    secret_key: str  # reference key only, never the token
    token_fingerprint: Optional[str] = None

    class Config:
        from_attributes = True
