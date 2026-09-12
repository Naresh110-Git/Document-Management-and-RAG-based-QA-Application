"""Authentication API tests."""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import UUID, uuid4

from fastapi.testclient import TestClient

from app.api.dependencies.auth import get_auth_service, get_current_active_user
from app.main import create_app
from app.models.user import UserRole
from app.schemas.auth import TokenPair
from app.schemas.user import UserCreate
from app.utils.request import RequestMetadata


@dataclass
class FakeUser:
    """Minimal user object compatible with UserRead.from_attributes."""

    email: str
    full_name: str | None = None
    id: UUID = field(default_factory=uuid4)
    role: UserRole = UserRole.USER
    is_active: bool = True
    is_verified: bool = False
    refresh_token_version: int = 0
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))


class FakeAuthService:
    """Small route-test double for AuthService."""

    async def register(self, payload: UserCreate, metadata: RequestMetadata) -> FakeUser:
        return FakeUser(email=str(payload.email), full_name=payload.full_name)

    async def login(self, payload, metadata: RequestMetadata) -> TokenPair:  # type: ignore[no-untyped-def]
        return TokenPair(access_token="access-token", refresh_token="refresh-token", expires_in=1800)

    async def refresh(self, refresh_token: str, metadata: RequestMetadata) -> TokenPair:
        return TokenPair(access_token="new-access-token", refresh_token="new-refresh-token", expires_in=1800)

    async def logout(self, current_user: FakeUser, metadata: RequestMetadata) -> None:
        current_user.refresh_token_version += 1


def build_client(current_user: FakeUser | None = None) -> TestClient:
    app = create_app()
    app.dependency_overrides[get_auth_service] = FakeAuthService
    if current_user is not None:
        app.dependency_overrides[get_current_active_user] = lambda: current_user
    return TestClient(app)


def test_register_returns_created_user() -> None:
    client = build_client()

    response = client.post(
        "/api/v1/register",
        json={"email": "USER@Example.com", "password": "LongEnough1!", "full_name": "User Example"},
    )

    assert response.status_code == 201
    assert response.json()["email"] == "user@example.com"
    assert response.json()["role"] == "user"


def test_login_returns_token_pair() -> None:
    client = build_client()

    response = client.post(
        "/api/v1/login",
        json={"email": "user@example.com", "password": "LongEnough1!"},
    )

    assert response.status_code == 200
    assert response.json()["access_token"] == "access-token"
    assert response.json()["token_type"] == "bearer"


def test_refresh_returns_new_token_pair() -> None:
    client = build_client()

    response = client.post("/api/v1/refresh", json={"refresh_token": "refresh-token"})

    assert response.status_code == 200
    assert response.json()["access_token"] == "new-access-token"


def test_me_returns_current_user() -> None:
    current_user = FakeUser(email="me@example.com", full_name="Current User")
    client = build_client(current_user=current_user)

    response = client.get("/api/v1/me", headers={"Authorization": "Bearer access-token"})

    assert response.status_code == 200
    assert response.json()["email"] == "me@example.com"


def test_logout_invalidates_refresh_token_version() -> None:
    current_user = FakeUser(email="me@example.com")
    client = build_client(current_user=current_user)

    response = client.post("/api/v1/logout", headers={"Authorization": "Bearer access-token"})

    assert response.status_code == 204
    assert current_user.refresh_token_version == 1
