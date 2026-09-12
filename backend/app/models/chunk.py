"""Document chunk model."""

from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import ForeignKey, Index, Integer, JSON, Text, UniqueConstraint, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.document import Document
    from app.models.embedding import Embedding


class Chunk(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Searchable document text chunk."""

    __tablename__ = "chunks"
    __table_args__ = (
        UniqueConstraint("document_id", "chunk_index", name="uq_chunks_document_chunk_index"),
        Index("ix_chunks_document_page", "document_id", "page_number"),
    )

    document_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
    )
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    page_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    token_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    char_start: Mapped[int | None] = mapped_column(Integer, nullable=True)
    char_end: Mapped[int | None] = mapped_column(Integer, nullable=True)
    chunk_metadata: Mapped[dict | None] = mapped_column("metadata", JSON, nullable=True)

    document: Mapped["Document"] = relationship(back_populates="chunks")
    embedding: Mapped["Embedding | None"] = relationship(
        back_populates="chunk",
        cascade="all, delete-orphan",
        passive_deletes=True,
        uselist=False,
    )
