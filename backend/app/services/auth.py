"""Authentication service."""

from datetime import timedelta
from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.exceptions import AuthenticationError, ConflictError
from app.core.security import (
    TokenExpiredError,
    TokenInvalidError,
    TokenType,
    create_jwt_token,
    decode_jwt_token,
    hash_password,
    verify_password,
)
from app.models.user import User, UserRole
from app.repositories.audit import AuditLogRepository
from app.repositories.user import UserRepository
from app.schemas.auth import LoginRequest, TokenPair
from app.schemas.user import UserCreate
from app.utils.request import RequestMetadata


class AuthService:
    """Business logic for registration, login, refresh, and logout."""

    def __init__(self, *, session: AsyncSession, settings: Settings) -> None:
        self.session = session
        self.settings = settings
        self.users = UserRepository(session)
        self.audit_logs = AuditLogRepository(session)

    async def register(self, payload: UserCreate, metadata: RequestMetadata) -> User:
        """Register a new normal user."""
        email = str(payload.email).lower()

        existing_user = await self.users.get_by_email(email)
        if existing_user is not None:
            raise ConflictError("A user with this email already exists", code="user_already_exists")

        try:
            user = await self.users.create(
                email=email,
                hashed_password=hash_password(
                    payload.password.get_secret_value(),
                    rounds=self.settings.bcrypt_rounds,
                ),
                full_name=payload.full_name,
                role=UserRole.USER,
            )
            await self.audit_logs.create(
                actor_user_id=user.id,
                action="auth.register",
                entity_type="user",
                entity_id=user.id,
                details={"email": email},
                ip_address=metadata.ip_address,
                user_agent=metadata.user_agent,
            )
            await self.session.commit()
            await self.session.refresh(user)
            return user
        except IntegrityError as exc:
            await self.session.rollback()
            raise ConflictError("A user with this email already exists", code="user_already_exists") from exc

    async def login(self, payload: LoginRequest, metadata: RequestMetadata) -> TokenPair:
        """Authenticate credentials and issue a token pair."""
        email = str(payload.email).lower()
        user = await self.users.get_by_email(email)
        password = payload.password.get_secret_value()

        if user is None or not verify_password(password, user.hashed_password):
            await self._audit_login_failure(email=email, metadata=metadata)
            raise AuthenticationError("Invalid email or password")

        if not user.is_active:
            await self._audit_login_failure(email=email, metadata=metadata, reason="inactive")
            raise AuthenticationError("User account is inactive")

        token_pair = self._issue_token_pair(user)
        await self.audit_logs.create(
            actor_user_id=user.id,
            action="auth.login_succeeded",
            entity_type="user",
            entity_id=user.id,
            details={"email": email},
            ip_address=metadata.ip_address,
            user_agent=metadata.user_agent,
        )
        await self.session.commit()
        return token_pair

    async def refresh(self, refresh_token: str, metadata: RequestMetadata) -> TokenPair:
        """Validate a refresh token and issue a new token pair."""
        try:
            payload = decode_jwt_token(refresh_token, settings=self.settings)
        except TokenExpiredError as exc:
            raise AuthenticationError("Refresh token has expired") from exc
        except TokenInvalidError as exc:
            raise AuthenticationError("Invalid refresh token") from exc

        if payload.get("typ") != TokenType.REFRESH.value:
            raise AuthenticationError("Refresh token required")

        user = await self._user_from_token_payload(payload)
        token_version = payload.get("token_version")
        if token_version != user.refresh_token_version:
            raise AuthenticationError("Refresh token has been revoked")

        if not user.is_active:
            raise AuthenticationError("User account is inactive")

        token_pair = self._issue_token_pair(user)
        await self.audit_logs.create(
            actor_user_id=user.id,
            action="auth.refresh",
            entity_type="user",
            entity_id=user.id,
            details={"email": user.email},
            ip_address=metadata.ip_address,
            user_agent=metadata.user_agent,
        )
        await self.session.commit()
        return token_pair

    async def logout(self, current_user: User, metadata: RequestMetadata) -> None:
        """Revoke previously issued refresh tokens for the current user."""
        await self.users.increment_refresh_token_version(current_user)
        await self.audit_logs.create(
            actor_user_id=current_user.id,
            action="auth.logout",
            entity_type="user",
            entity_id=current_user.id,
            details={"email": current_user.email},
            ip_address=metadata.ip_address,
            user_agent=metadata.user_agent,
        )
        await self.session.commit()

    def _issue_token_pair(self, user: User) -> TokenPair:
        """Issue access and refresh tokens for a user."""
        role = user.role.value if isinstance(user.role, UserRole) else str(user.role)
        access_delta = timedelta(minutes=self.settings.access_token_expire_minutes)
        refresh_delta = timedelta(days=self.settings.refresh_token_expire_days)

        return TokenPair(
            access_token=create_jwt_token(
                subject=user.id,
                email=user.email,
                role=role,
                token_type=TokenType.ACCESS,
                expires_delta=access_delta,
                settings=self.settings,
            ),
            refresh_token=create_jwt_token(
                subject=user.id,
                email=user.email,
                role=role,
                token_type=TokenType.REFRESH,
                expires_delta=refresh_delta,
                settings=self.settings,
                token_version=user.refresh_token_version,
            ),
            expires_in=int(access_delta.total_seconds()),
        )

    async def _user_from_token_payload(self, payload: dict[str, object]) -> User:
        """Resolve and validate the subject user from a JWT payload."""
        try:
            user_id = UUID(str(payload["sub"]))
        except (KeyError, TypeError, ValueError) as exc:
            raise AuthenticationError("Invalid token subject") from exc

        user = await self.users.get_by_id(user_id)
        if user is None:
            raise AuthenticationError("User not found")
        return user

    async def _audit_login_failure(
        self,
        *,
        email: str,
        metadata: RequestMetadata,
        reason: str = "invalid_credentials",
    ) -> None:
        """Persist a failed login attempt."""
        await self.audit_logs.create(
            action="auth.login_failed",
            entity_type="user",
            details={"email": email, "reason": reason},
            ip_address=metadata.ip_address,
            user_agent=metadata.user_agent,
        )
        await self.session.commit()
