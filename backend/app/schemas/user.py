"""User schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, SecretStr, field_validator

from app.core.security import MAX_BCRYPT_PASSWORD_BYTES
from app.models.user import UserRole


class UserCreate(BaseModel):
    """Public user registration payload."""

    model_config = ConfigDict(extra="forbid")

    email: EmailStr
    password: SecretStr = Field(min_length=8)
    full_name: str | None = Field(default=None, max_length=255)

    @field_validator("email", mode="after")
    @classmethod
    def normalize_email(cls, value: EmailStr) -> str:
        """Store emails in a normalized form."""
        return str(value).lower()

    @field_validator("password")
    @classmethod
    def validate_password_length(cls, value: SecretStr) -> SecretStr:
        """Reject passwords that bcrypt would silently truncate."""
        if len(value.get_secret_value().encode("utf-8")) > MAX_BCRYPT_PASSWORD_BYTES:
            raise ValueError("Password must be 72 bytes or fewer")
        return value


class UserRead(BaseModel):
    """Public user profile response."""

    model_config = ConfigDict(from_attributes=True, extra="forbid")

    id: UUID
    email: EmailStr
    full_name: str | None
    role: UserRole
    is_active: bool
    is_verified: bool
    created_at: datetime
    updated_at: datetime
