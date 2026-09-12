"""Document repository."""

from typing import List
from uuid import UUID

from sqlalchemy import select, delete, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document import Document, DocumentStatus


class DocumentRepository:
    """Persistence operations for document records."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(
        self,
        *,
        owner_id: UUID,
        title: str,
        original_filename: str,
        stored_filename: str,
        storage_path: str,
        content_type: str,
        file_size: int,
        checksum_sha256: str,
        page_count: int | None = None,
    ) -> Document:
        doc = Document(
            owner_id=owner_id,
            title=title,
            original_filename=original_filename,
            stored_filename=stored_filename,
            storage_path=storage_path,
            content_type=content_type,
            file_size=file_size,
            checksum_sha256=checksum_sha256,
            page_count=page_count,
            status=DocumentStatus.READY if page_count is not None else DocumentStatus.UPLOADED,
        )
        self.session.add(doc)
        await self.session.flush()
        return doc

    async def get_by_id(self, document_id: UUID) -> Document | None:
        result = await self.session.execute(select(Document).where(Document.id == document_id))
        return result.scalar_one_or_none()

    async def list_by_owner(self, owner_id: UUID) -> List[Document]:
        result = await self.session.execute(select(Document).where(Document.owner_id == owner_id))
        return result.scalars().all()

    async def delete(self, document: Document) -> None:
        await self.session.execute(delete(Document).where(Document.id == document.id))

    async def update_title(self, document: Document, title: str) -> Document:
        await self.session.execute(
            update(Document).where(Document.id == document.id).values(title=title)
        )
        await self.session.flush()
        return document

    async def mark_status(self, document: Document, status: DocumentStatus, error_message: str | None = None) -> Document:
        document.status = status
        document.error_message = error_message
        await self.session.flush()
        return document
