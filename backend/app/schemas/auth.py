"""Authentication request and response schemas."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, SecretStr, field_validator

from app.core.security import MAX_BCRYPT_PASSWORD_BYTES


class LoginRequest(BaseModel):
    """Login request payload."""

    model_config = ConfigDict(extra="forbid")

    email: EmailStr
    password: SecretStr = Field(min_length=8)

    @field_validator("email", mode="after")
    @classmethod
    def normalize_email(cls, value: EmailStr) -> str:
        """Store and compare emails case-insensitively."""
        return str(value).lower()

    @field_validator("password")
    @classmethod
    def validate_password_length(cls, value: SecretStr) -> SecretStr:
        """Reject passwords that bcrypt would silently truncate."""
        if len(value.get_secret_value().encode("utf-8")) > MAX_BCRYPT_PASSWORD_BYTES:
            raise ValueError("Password must be 72 bytes or fewer")
        return value


class RefreshTokenRequest(BaseModel):
    """Refresh token request payload."""

    model_config = ConfigDict(extra="forbid")

    refresh_token: str = Field(min_length=1)


class TokenPair(BaseModel):
    """Access and refresh token response."""

    model_config = ConfigDict(extra="forbid")

    access_token: str
    refresh_token: str
    token_type: Literal["bearer"] = "bearer"
    expires_in: int
