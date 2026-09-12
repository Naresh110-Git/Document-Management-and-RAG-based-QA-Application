"""Embedding model."""

from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import ForeignKey, Index, Integer, JSON, String, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.chunk import Chunk

DEFAULT_EMBEDDING_DIMENSIONS = 384

try:
    from pgvector.sqlalchemy import Vector
except ImportError:
    from sqlalchemy import JSON

    def Vector(dimensions: int) -> JSON:  # type: ignore[no-redef]
        """Fallback type so metadata can be imported without pgvector installed."""
        return JSON()


class Embedding(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Vector embedding for a document chunk."""

    __tablename__ = "embeddings"
    __table_args__ = (
        Index("ix_embeddings_model", "model_name"),
        Index("ix_embeddings_chunk", "chunk_id"),
    )

    chunk_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("chunks.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )
    provider: Mapped[str] = mapped_column(String(50), nullable=False)
    model_name: Mapped[str] = mapped_column(String(255), nullable=False)
    dimension: Mapped[int] = mapped_column(Integer, default=DEFAULT_EMBEDDING_DIMENSIONS, nullable=False)
    vector: Mapped[list[float]] = mapped_column(Vector(DEFAULT_EMBEDDING_DIMENSIONS), nullable=False)
    embedding_metadata: Mapped[dict | None] = mapped_column("metadata", JSON, nullable=True)

    chunk: Mapped["Chunk"] = relationship(back_populates="embedding")
