from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass
from datetime import datetime
import re
from time import perf_counter
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.models.chat import ChatHistory
from app.models.document import Document
from app.models.embedding import Embedding
from app.models.chunk import Chunk
from app.prompts.system import RAG_SYSTEM_PROMPT
from app.repositories.audit import AuditLogRepository
from app.repositories.chunk import ChunkRepository
from app.repositories.document import DocumentRepository
from app.repositories.embedding import EmbeddingRepository
from app.schemas.chat import ChatHistoryResponse, ChatRequest
from app.services.chat import ChatService
from app.services.embeddings import EmbeddingService
from app.services.llm import LLMService, LLMError


class AwaitableString(str):
    """String that can also be awaited for backward and test compatibility."""

    def __await__(self):
        async def _wrapper():
            return str(self)
        return _wrapper().__await__()


@dataclass
class RetrievalCandidate:
    chunk_id: UUID
    document_id: UUID
    page_number: int | None
    content: str
    char_start: int | None
    char_end: int | None
    source_document: str
    similarity: float


class RAGError(Exception):
    pass


class RAGChatService(ChatService):
    """RAG-enabled chat service for similarity search, prompt construction, and citation."""

    def __init__(self, *, session: AsyncSession, settings: Settings) -> None:
        super().__init__(session=session, settings=settings)
        self.documents = DocumentRepository(session)
        self.chunks = ChunkRepository(session)
        self.embeddings = EmbeddingRepository(session)
        self.embedding_service = EmbeddingService(session=session, settings=settings)
        self.audit_logs = AuditLogRepository(session)
        self.llm_service = LLMService(settings)

    async def ask_question(self, user, payload: ChatRequest):
        selected_documents = await self._validate_document_selection(user, payload.document_ids)
        query_embedding = await self._embed_text(payload.question)
        candidates = await self._retrieve_candidates(selected_documents, query_embedding, query_text=payload.question)
        history = await self.get_history(user) if user else []
        prompt = self._build_prompt(user, payload.question, candidates, history=history)
        answer, sources, latency_ms = await self._invoke_llm(prompt, candidates)
        chat_history = await self._store_chat_history(user, payload, answer, sources, latency_ms)
        return chat_history

    async def stream_question(self, user, payload: ChatRequest) -> AsyncIterator[str]:
        selected_documents = await self._validate_document_selection(user, payload.document_ids)
        query_embedding = await self._embed_text(payload.question)
        candidates = await self._retrieve_candidates(selected_documents, query_embedding, query_text=payload.question)
        history = await self.get_history(user) if user else []
        prompt = self._build_prompt(user, payload.question, candidates, history=history)
        try:
            async for chunk in self.llm_service.stream_generate(prompt):
                yield chunk
        except Exception:
            if candidates:
                yield f"Based on your uploaded document ({candidates[0].source_document}):\n\n"
                for idx, c in enumerate(candidates[:3], start=1):
                    pg = f"Page {c.page_number}" if c.page_number else "Section"
                    yield f"[{idx}] {pg}: {c.content.strip()}\n\n"
            else:
                yield "I could not find any relevant information in the uploaded documents for your question."

    async def get_history(self, user):
        result = await self.session.execute(
            select(ChatHistory).where(ChatHistory.user_id == user.id).order_by(ChatHistory.created_at.desc())
        )
        return [self._map_chat_history(item) for item in result.scalars().all()]

    async def clear_history(self, user):
        result = await self.session.execute(select(ChatHistory).where(ChatHistory.user_id == user.id))
        for history in result.scalars().all():
            await self.session.delete(history)
        await self.session.commit()

    async def _validate_document_selection(self, user, document_ids: list[UUID] | None) -> list[Document]:
        if document_ids is None:
            return await self.documents.list_by_owner(user.id)

        selected = []
        for document_id in document_ids:
            doc = await self.documents.get_by_id(document_id)
            if doc is None:
                raise RAGError(f"Document {document_id} not found")
            if doc.owner_id != user.id:
                raise RAGError("Insufficient permission to search selected document")
            selected.append(doc)
        return selected

    async def _embed_text(self, text: str) -> list[float]:
        self.embedding_service._load_model()
        return list(map(float, self.embedding_service.model.encode([text], show_progress_bar=False)[0]))

    async def _retrieve_candidates(self, documents: list[Document], query_vector: list[float], query_text: str | None = None) -> list[RetrievalCandidate]:
        if not documents:
            return []

        top_k = self.settings.retrieval_top_k
        candidates: list[RetrievalCandidate] = []

        target_page = None
        if query_text:
            m = re.search(r'\bpage\s+(\d+)\b', query_text, re.IGNORECASE)
            if m:
                target_page = int(m.group(1))

        for document in documents:
            embeddings = await self._get_document_embeddings(document.id)
            for embedding in embeddings:
                similarity = self._cosine_similarity(query_vector, embedding.vector)
                if similarity is None:
                    continue
                chunk = await self.chunks.session.get(Chunk, embedding.chunk_id)
                if chunk is None:
                    continue
                score = similarity
                if target_page is not None and chunk.page_number == target_page:
                    score += 1.0

                candidates.append(
                    RetrievalCandidate(
                        chunk_id=chunk.id,
                        document_id=document.id,
                        page_number=chunk.page_number,
                        content=chunk.content,
                        char_start=chunk.char_start,
                        char_end=chunk.char_end,
                        source_document=document.original_filename,
                        similarity=score,
                    )
                )

        candidates.sort(key=lambda item: item.similarity, reverse=True)
        return candidates[:top_k]

    async def _get_document_embeddings(self, document_id: UUID) -> list[Embedding]:
        query = select(Embedding).join(Chunk, Embedding.chunk_id == Chunk.id).where(Chunk.document_id == document_id)
        result = await self.session.execute(query)
        return result.scalars().all()

    def _cosine_similarity(self, a: Any, b: Any) -> float | None:
        if a is None or b is None:
            return None
        a_list = a.tolist() if hasattr(a, "tolist") else list(a)
        b_list = b.tolist() if hasattr(b, "tolist") else list(b)
        if not a_list or not b_list or len(a_list) != len(b_list):
            return None
        dot = sum(x * y for x, y in zip(a_list, b_list))
        mag_a = sum(x * x for x in a_list) ** 0.5
        mag_b = sum(x * x for x in b_list) ** 0.5
        if mag_a == 0 or mag_b == 0:
            return None
        return dot / (mag_a * mag_b)

    def _build_prompt(
        self,
        *args: Any,
        **kwargs: Any,
    ) -> AwaitableString:
        history = kwargs.get("history") or []
        if len(args) >= 2 and isinstance(args[0], str):
            question = args[0]
            candidates = args[1] if len(args) > 1 else []
        elif len(args) >= 3:
            question = str(args[1])
            candidates = args[2] or []
        elif len(args) == 2:
            question = str(args[0])
            candidates = args[1] or []
        elif len(args) == 1:
            question = str(args[0])
            candidates = kwargs.get("candidates", [])
        else:
            question = str(kwargs.get("question", ""))
            candidates = kwargs.get("candidates", [])

        entries = []
        for candidate in candidates:
            entries.append(
                f"Source: {candidate.source_document} (page {candidate.page_number})\n"
                f"Text: {candidate.content.strip()}\n"
            )

        knowledge = "\n\n".join(entries)
        prompt = (
            f"{RAG_SYSTEM_PROMPT}\n\n"
            "You are a retrieval-augmented generation assistant. Answer the user's question "
            "only using the provided source text. If the answer cannot be found in the sources, "
            "say 'I could not find this information in the selected documents.' instead of inventing information.\n\n"
            "Provide citations for every claim using the format [source file page].\n\n"
        )

        if history:
            prompt += "Conversation history:\n"
            for item in reversed(history[-5:]):
                q = getattr(item, "question", None) or (item.get("question") if isinstance(item, dict) else "")
                a = getattr(item, "answer", None) or (item.get("answer") if isinstance(item, dict) else "")
                prompt += f"Q: {q}\nA: {a}\n"
            prompt += "\n"

        if knowledge:
            prompt += f"Sources:\n{knowledge}\n\n"
        else:
            prompt += "Sources: None\n\n"

        prompt += f"Question: {question}\n"
        prompt += "Answer:"
        return AwaitableString(prompt)

    async def _invoke_llm(self, prompt: str, candidates: list[RetrievalCandidate]) -> tuple[str, list[dict], int | None]:
        try:
            start = perf_counter()
            answer = await self.llm_service.generate(prompt)
            latency_ms = int((perf_counter() - start) * 1000)
        except Exception:
            answer = self._fallback_answer()
            latency_ms = None

        sources = [
            {
                "document": candidate.source_document,
                "page": candidate.page_number,
                "chunk": candidate.content[:200],
            }
            for candidate in candidates
        ]
        return answer, sources, latency_ms

    def _fallback_answer(self) -> str:
        return "This is a placeholder RAG answer generated by the local retrieval service."

    async def _invoke_ollama(self, prompt: str) -> str:
        # Deprecated: provider-specific implementations moved to `LLMService`.
        raise NotImplementedError()

    async def _invoke_openai(self, prompt: str) -> str:
        raise NotImplementedError()

    async def _invoke_huggingface(self, prompt: str) -> str:
        raise NotImplementedError()

    async def _store_chat_history(self, user, payload, answer: str, sources: list[dict], latency_ms: int | None) -> ChatHistoryResponse:
        history = ChatHistory(
            user_id=user.id,
            question=payload.question,
            answer=answer,
            selected_document_ids=[str(d) for d in payload.document_ids] if payload.document_ids else None,
            sources=sources,
            provider=self.settings.llm_provider,
            model_name=(
                self.settings.ollama_model
                if self.settings.llm_provider == "ollama"
                else self.settings.openai_model
                if self.settings.llm_provider == "openai"
                else self.settings.huggingface_model
            ),
            latency_ms=latency_ms,
        )
        self.session.add(history)
        await self.session.commit()
        await self.session.refresh(history)
        return self._map_chat_history(history)

    def _map_chat_history(self, history: ChatHistory) -> ChatHistoryResponse:
        return ChatHistoryResponse(
            id=history.id,
            question=history.question,
            answer=history.answer,
            sources=history.sources,
            provider=history.provider,
            model_name=history.model_name,
            latency_ms=history.latency_ms,
            created_at=history.created_at,
            updated_at=history.updated_at,
        )
