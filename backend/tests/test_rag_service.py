import pytest
from uuid import UUID, uuid4

from app.services.rag import RAGChatService, RetrievalCandidate
from app.schemas.chat import ChatRequest
from app.services.embeddings import EmbeddingService
from app.core.config import Settings


class DummyModel:
    def encode(self, texts, show_progress_bar=False):
        return [[0.1] * 384 for _ in texts]


class DummySession:
    pass


@pytest.mark.asyncio
async def test_retrieve_candidates_with_empty_docs(monkeypatch):
    settings = Settings()
    service = RAGChatService(session=DummySession(), settings=settings)

    monkeypatch.setattr(service, "_get_document_embeddings", lambda document_id: [])
    candidates = await service._retrieve_candidates([], [0.1] * 384)
    assert candidates == []


def test_build_prompt_includes_sources():
    settings = Settings()
    service = RAGChatService(session=DummySession(), settings=settings)
    candidates = [
        RetrievalCandidate(
            chunk_id=uuid4(),
            document_id=uuid4(),
            page_number=1,
            content="This is a test chunk.",
            char_start=0,
            char_end=21,
            source_document="doc.pdf",
            similarity=0.92,
        )
    ]
    prompt = service._build_prompt("What is this?", candidates)
    assert "Source: doc.pdf (page 1)" in prompt
    assert "This is a test chunk." in prompt
    assert "Question: What is this?" in prompt
