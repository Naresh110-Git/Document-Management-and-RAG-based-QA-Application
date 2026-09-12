"""Chat history model."""

from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import ForeignKey, Index, Integer, JSON, String, Text, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.user import User


class ChatHistory(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Stored question/answer exchange with source metadata."""

    __tablename__ = "chat_history"
    __table_args__ = (Index("ix_chat_history_user_created_at", "user_id", "created_at"),)

    user_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    question: Mapped[str] = mapped_column(Text, nullable=False)
    answer: Mapped[str] = mapped_column(Text, nullable=False)
    selected_document_ids: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    sources: Mapped[list[dict] | None] = mapped_column(JSON, nullable=True)
    provider: Mapped[str | None] = mapped_column(String(50), nullable=True)
    model_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)

    user: Mapped["User"] = relationship(back_populates="chat_history")
