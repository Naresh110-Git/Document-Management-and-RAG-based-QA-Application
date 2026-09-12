"""Authentication and authorization dependencies."""

from collections.abc import Awaitable, Callable
from typing import Annotated
from uuid import UUID

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.exceptions import AuthenticationError, AuthorizationError
from app.core.security import TokenExpiredError, TokenInvalidError, TokenType, decode_jwt_token
from app.database.session import get_db
from app.models.user import User, UserRole
from app.repositories.user import UserRepository
from app.services.auth import AuthService

bearer_scheme = HTTPBearer(auto_error=False)


async def get_auth_service(
    db: Annotated[AsyncSession, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> AuthService:
    """Build the authentication service for request handlers."""
    return AuthService(session=db, settings=settings)


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    db: Annotated[AsyncSession, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> User:
    """Resolve the user represented by the bearer access token."""
    if credentials is None:
        raise AuthenticationError("Missing bearer token")

    try:
        payload = decode_jwt_token(credentials.credentials, settings=settings)
    except TokenExpiredError as exc:
        raise AuthenticationError("Access token has expired") from exc
    except TokenInvalidError as exc:
        raise AuthenticationError("Invalid access token") from exc

    if payload.get("typ") != TokenType.ACCESS.value:
        raise AuthenticationError("Access token required")

    try:
        user_id = UUID(str(payload["sub"]))
    except (KeyError, TypeError, ValueError) as exc:
        raise AuthenticationError("Invalid access token subject") from exc

    user = await UserRepository(db).get_by_id(user_id)
    if user is None:
        raise AuthenticationError("User not found")

    return user


async def get_current_active_user(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    """Require an authenticated active user."""
    if not current_user.is_active:
        raise AuthorizationError("User account is inactive")
    return current_user


def require_roles(*allowed_roles: UserRole) -> Callable[..., Awaitable[User]]:
    """Return a dependency that enforces role-based access control."""
    allowed_values = {role.value for role in allowed_roles}

    async def role_dependency(
        current_user: Annotated[User, Depends(get_current_active_user)],
    ) -> User:
        current_role = (
            current_user.role.value if isinstance(current_user.role, UserRole) else str(current_user.role)
        )
        if current_role not in allowed_values:
            raise AuthorizationError("Insufficient permissions", code="insufficient_permissions")
        return current_user

    return role_dependency


CurrentUser = Annotated[User, Depends(get_current_active_user)]
AdminUser = Annotated[User, Depends(require_roles(UserRole.ADMIN))]
AuthServiceDependency = Annotated[AuthService, Depends(get_auth_service)]
