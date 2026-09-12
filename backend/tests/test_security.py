"""Security helper tests."""

from datetime import timedelta
from uuid import uuid4

import pytest

from app.core.config import Settings
from app.core.security import (
    TokenExpiredError,
    TokenType,
    create_jwt_token,
    decode_jwt_token,
    hash_password,
    verify_password,
)


def test_password_hashing_uses_bcrypt_and_verifies() -> None:
    password_hash = hash_password("LongEnough1!", rounds=12)

    assert password_hash.startswith("$2")
    assert verify_password("LongEnough1!", password_hash)
    assert not verify_password("wrong-password", password_hash)


def test_jwt_round_trip_contains_expected_claims() -> None:
    settings = Settings(jwt_secret_key="test-secret")
    user_id = uuid4()

    token = create_jwt_token(
        subject=user_id,
        email="user@example.com",
        role="user",
        token_type=TokenType.ACCESS,
        expires_delta=timedelta(minutes=5),
        settings=settings,
    )
    payload = decode_jwt_token(token, settings=settings)

    assert payload["sub"] == str(user_id)
    assert payload["email"] == "user@example.com"
    assert payload["role"] == "user"
    assert payload["typ"] == "access"


def test_expired_jwt_raises_token_expired_error() -> None:
    settings = Settings(jwt_secret_key="test-secret")
    token = create_jwt_token(
        subject=uuid4(),
        email="user@example.com",
        role="user",
        token_type=TokenType.ACCESS,
        expires_delta=timedelta(seconds=-1),
        settings=settings,
    )

    with pytest.raises(TokenExpiredError):
        decode_jwt_token(token, settings=settings)
