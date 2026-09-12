"""Chunk repository."""

from typing import List
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.chunk import Chunk


class ChunkRepository:
    """Persistence operations for document chunks."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(
        self,
        *,
        document_id: UUID,
        chunk_index: int,
        page_number: int | None,
        content: str,
        char_start: int | None = None,
        char_end: int | None = None,
        token_count: int | None = None,
        metadata: dict | None = None,
    ) -> Chunk:
        chunk = Chunk(
            document_id=document_id,
            chunk_index=chunk_index,
            page_number=page_number,
            content=content,
            char_start=char_start,
            char_end=char_end,
            token_count=token_count,
            chunk_metadata=metadata,
        )
        self.session.add(chunk)
        await self.session.flush()
        return chunk

    async def list_by_document(self, document_id: UUID) -> List[Chunk]:
        result = await self.session.execute(select(Chunk).where(Chunk.document_id == document_id))
        return result.scalars().all()
