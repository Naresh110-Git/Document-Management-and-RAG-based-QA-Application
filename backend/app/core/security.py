"""Password hashing and JWT helpers."""

from datetime import UTC, datetime, timedelta
from enum import Enum
from uuid import UUID, uuid4

import bcrypt
import jwt

from app.core.config import Settings

MAX_BCRYPT_PASSWORD_BYTES = 72


class TokenType(str, Enum):
    """Supported JWT token types."""

    ACCESS = "access"
    REFRESH = "refresh"


class TokenError(Exception):
    """Base token validation error."""


class TokenExpiredError(TokenError):
    """Raised when a JWT has expired."""


class TokenInvalidError(TokenError):
    """Raised when a JWT is malformed or fails verification."""


def hash_password(password: str, *, rounds: int = 12) -> str:
    """Hash a plaintext password using bcrypt."""
    password_bytes = password.encode("utf-8")
    if len(password_bytes) > MAX_BCRYPT_PASSWORD_BYTES:
        raise ValueError("Password exceeds bcrypt's 72-byte limit")

    return bcrypt.hashpw(password_bytes, bcrypt.gensalt(rounds=rounds)).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    """Verify a plaintext password against a bcrypt hash."""
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except ValueError:
        return False


def create_jwt_token(
    *,
    subject: UUID,
    email: str,
    role: str,
    token_type: TokenType,
    expires_delta: timedelta,
    settings: Settings,
    token_version: int | None = None,
) -> str:
    """Create a signed JWT for a user."""
    now = datetime.now(UTC)
    payload: dict[str, object] = {
        "sub": str(subject),
        "email": email,
        "role": role,
        "typ": token_type.value,
        "iat": now,
        "exp": now + expires_delta,
        "jti": str(uuid4()),
    }

    if token_version is not None:
        payload["token_version"] = token_version

    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def decode_jwt_token(token: str, *, settings: Settings) -> dict[str, object]:
    """Decode and validate a signed JWT."""
    try:
        return jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
    except jwt.ExpiredSignatureError as exc:
        raise TokenExpiredError("Token has expired") from exc
    except jwt.InvalidTokenError as exc:
        raise TokenInvalidError("Token is invalid") from exc
