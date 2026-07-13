from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1, max_length=256)


class LoginResponse(BaseModel):
    username: str
    role: str
    csrf_token: str


class AuthStatusResponse(BaseModel):
    authenticated: bool
    username: str | None = None
    role: str | None = None
