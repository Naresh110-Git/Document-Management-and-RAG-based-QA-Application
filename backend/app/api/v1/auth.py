"""Authentication endpoints."""

from fastapi import APIRouter, Request, Response, status

from app.api.dependencies.auth import AuthServiceDependency, CurrentUser
from app.schemas.auth import LoginRequest, RefreshTokenRequest, TokenPair
from app.schemas.user import UserCreate, UserRead
from app.utils.request import request_metadata_from

router = APIRouter(tags=["Authentication"])


@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
async def register(
    payload: UserCreate,
    request: Request,
    auth_service: AuthServiceDependency,
) -> UserRead:
    """Register a new normal user account."""
    user = await auth_service.register(payload, request_metadata_from(request))
    return UserRead.model_validate(user)


@router.post("/login", response_model=TokenPair)
async def login(
    payload: LoginRequest,
    request: Request,
    auth_service: AuthServiceDependency,
) -> TokenPair:
    """Authenticate a user and return access and refresh tokens."""
    return await auth_service.login(payload, request_metadata_from(request))


@router.post("/refresh", response_model=TokenPair)
async def refresh(
    payload: RefreshTokenRequest,
    request: Request,
    auth_service: AuthServiceDependency,
) -> TokenPair:
    """Exchange a valid refresh token for a new token pair."""
    return await auth_service.refresh(payload.refresh_token, request_metadata_from(request))


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    request: Request,
    current_user: CurrentUser,
    auth_service: AuthServiceDependency,
) -> Response:
    """Invalidate future refresh-token use for the current user."""
    await auth_service.logout(current_user, request_metadata_from(request))
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/me", response_model=UserRead)
async def read_current_user(current_user: CurrentUser) -> UserRead:
    """Return the authenticated user's profile."""
    return UserRead.model_validate(current_user)
