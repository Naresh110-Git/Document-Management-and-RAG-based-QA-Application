"""User repository."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User, UserRole


class UserRepository:
    """Persistence operations for user records."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_id(self, user_id: UUID) -> User | None:
        """Return a user by id."""
        result = await self.session.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> User | None:
        """Return a user by normalized email."""
        result = await self.session.execute(select(User).where(User.email == email.lower()))
        return result.scalar_one_or_none()

    async def create(
        self,
        *,
        email: str,
        hashed_password: str,
        full_name: str | None = None,
        role: UserRole = UserRole.USER,
    ) -> User:
        """Create a user without committing the transaction."""
        user = User(
            email=email.lower(),
            hashed_password=hashed_password,
            full_name=full_name,
            role=role,
        )
        self.session.add(user)
        await self.session.flush()
        return user

    async def increment_refresh_token_version(self, user: User) -> User:
        """Invalidate previously issued refresh tokens for a user."""
        user.refresh_token_version += 1
        await self.session.flush()
        return user
