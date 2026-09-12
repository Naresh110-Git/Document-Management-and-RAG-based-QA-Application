"""User model."""

import enum
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Enum as SAEnum, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.audit import AuditLog
    from app.models.chat import ChatHistory
    from app.models.document import Document


class UserRole(str, enum.Enum):
    """Application roles."""

    ADMIN = "admin"
    USER = "user"


class User(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Application user account."""

    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(320), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    role: Mapped[UserRole] = mapped_column(
        SAEnum(
            UserRole,
            name="user_role",
            values_callable=lambda enum_cls: [item.value for item in enum_cls],
        ),
        default=UserRole.USER,
        nullable=False,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    refresh_token_version: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    documents: Mapped[list["Document"]] = relationship(
        back_populates="owner",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    chat_history: Mapped[list["ChatHistory"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    audit_logs: Mapped[list["AuditLog"]] = relationship(back_populates="actor")
