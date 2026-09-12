"""Embedding generation and vector storage service.

Supports `sentence-transformers` models and stores vectors in the Embedding table
backed by `pgvector`. Optionally supports FAISS as an alternative vector backend.
"""

from __future__ import annotations

from typing import List
from uuid import UUID
import math

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.repositories.embedding import EmbeddingRepository
from app.repositories.chunk import ChunkRepository

try:
    from sentence_transformers import SentenceTransformer
except Exception:
    SentenceTransformer = None


class EmbeddingError(Exception):
    pass


class EmbeddingService:
    def __init__(self, *, session: AsyncSession, settings: Settings) -> None:
        self.session = session
        self.settings = settings
        self.embedding_repo = EmbeddingRepository(session)
        self.chunk_repo = ChunkRepository(session)
        self.model = None

    def _load_model(self):
        if self.model is not None:
            return
        model_name = self.settings.active_embedding_model
        if SentenceTransformer is None:
            raise EmbeddingError("sentence-transformers is not installed")
        self.model = SentenceTransformer(model_name)

    async def embed_chunks_for_document(self, document_id: UUID, batch_size: int = 32) -> int:
        """Compute embeddings for all chunks of a document and persist them.

        Returns the number of embeddings created.
        """
        self._load_model()

        chunks = await self.chunk_repo.list_by_document(document_id)
        if not chunks:
            return 0

        texts = [c.content for c in chunks]
        total = 0

        for i in range(0, len(texts), batch_size):
            batch_texts = texts[i : i + batch_size]
            vectors = self.model.encode(batch_texts, show_progress_bar=False)
            for chunk_obj, vec in zip(chunks[i : i + batch_size], vectors):
                dim = len(vec) if hasattr(vec, "__len__") else 0
                await self.embedding_repo.create(
                    chunk_id=chunk_obj.id,
                    provider="local_sentence_transformer",
                    model_name=self.settings.active_embedding_model,
                    vector=list(map(float, vec.tolist() if hasattr(vec, "tolist") else vec)),
                    dimension=dim,
                )
                total += 1

        await self.session.commit()
        return total
