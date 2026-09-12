"""Embedding repository."""

from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.embedding import Embedding


class EmbeddingRepository:
    """Persistence for embeddings."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(
        self,
        *,
        chunk_id: UUID,
        provider: str,
        model_name: str,
        vector: list[float],
        dimension: int,
        metadata: dict | None = None,
    ) -> Embedding:
        emb = Embedding(
            chunk_id=chunk_id,
            provider=provider,
            model_name=model_name,
            dimension=dimension,
            vector=vector,
            embedding_metadata=metadata,
        )
        self.session.add(emb)
        await self.session.flush()
        return emb
