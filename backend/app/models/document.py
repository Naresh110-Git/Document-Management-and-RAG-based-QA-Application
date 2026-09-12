"""Document model."""

import enum
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import BigInteger, Enum as SAEnum, ForeignKey, Index, Integer, JSON, String, Text, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.chunk import Chunk
    from app.models.user import User


class DocumentStatus(str, enum.Enum):
    """Lifecycle states for an uploaded document."""

    UPLOADED = "uploaded"
    PROCESSING = "processing"
    READY = "ready"
    FAILED = "failed"
    DELETED = "deleted"


class Document(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Uploaded source document and metadata."""

    __tablename__ = "documents"
    __table_args__ = (
        Index("ix_documents_owner_status", "owner_id", "status"),
        Index("ix_documents_checksum", "checksum_sha256"),
    )

    owner_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    stored_filename: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    storage_path: Mapped[str] = mapped_column(Text, nullable=False)
    content_type: Mapped[str] = mapped_column(String(120), nullable=False)
    file_size: Mapped[int] = mapped_column(BigInteger, nullable=False)
    checksum_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    page_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[DocumentStatus] = mapped_column(
        SAEnum(
            DocumentStatus,
            name="document_status",
            values_callable=lambda enum_cls: [item.value for item in enum_cls],
        ),
        default=DocumentStatus.UPLOADED,
        nullable=False,
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    doc_metadata: Mapped[dict | None] = mapped_column("metadata", JSON, nullable=True)

    owner: Mapped["User"] = relationship(back_populates="documents")
    chunks: Mapped[list["Chunk"]] = relationship(
        back_populates="document",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
