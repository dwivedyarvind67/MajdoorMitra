from pydantic import BaseModel, Field, field_validator
import re


class RegisterRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    phone: str = Field(..., pattern=r'^[6-9]\d{9}$')
    pin: str = Field(..., min_length=4, max_length=6)
    preferred_language: str = Field(default="hi", pattern=r'^(hi|en)$')

    @field_validator('pin')
    @classmethod
    def pin_must_be_digits(cls, v):
        if not v.isdigit():
            raise ValueError('PIN must contain only digits')
        return v


class LoginRequest(BaseModel):
    phone: str = Field(..., pattern=r'^[6-9]\d{9}$')
    pin: str = Field(..., min_length=4, max_length=6)


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    worker_id: str
    name: str


class WorkerProfile(BaseModel):
    id: str
    name: str
    phone: str
    preferred_language: str
