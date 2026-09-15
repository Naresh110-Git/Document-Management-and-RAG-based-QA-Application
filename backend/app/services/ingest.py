"""Document ingestion pipeline: extract PDF text, split into chunks, store in DB."""

from __future__ import annotations

from typing import List
from uuid import UUID
import asyncio
from pathlib import Path
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.repositories.chunk import ChunkRepository
from app.repositories.document import DocumentRepository
from app.repositories.audit import AuditLogRepository
from app.models.document import DocumentStatus
from app.services.embeddings import EmbeddingService

try:
    import fitz  # PyMuPDF
except Exception:
    fitz = None

try:
    import pdfplumber
except Exception:
    pdfplumber = None

try:
    from langchain_text_splitters import RecursiveCharacterTextSplitter
except Exception:
    try:
        from langchain.text_splitter import RecursiveCharacterTextSplitter
    except Exception:
        RecursiveCharacterTextSplitter = None


@dataclass
class PageText:
    page_number: int
    text: str


class IngestionError(Exception):
    pass


class IngestionService:
    """Extract text from PDFs, split into chunks, and persist them."""

    def __init__(self, *, session: AsyncSession, settings: Settings) -> None:
        self.session = session
        self.settings = settings
        self.chunks = ChunkRepository(session)
        self.documents = DocumentRepository(session)
        self.audit_logs = AuditLogRepository(session)

    async def process_document(self, document_id: UUID) -> None:
        doc = await self.documents.get_by_id(document_id)
        if doc is None:
            raise IngestionError("Document not found")

        if doc.status == DocumentStatus.READY:
            return

        await self.documents.mark_status(doc, DocumentStatus.PROCESSING)

        path = Path(doc.storage_path)
        if not path.exists():
            await self.documents.mark_status(doc, doc.status if doc.status else None, error_message="file_missing")
            raise IngestionError("Stored file not found")


        # extract pages
        pages = self._extract_pages(path)

        if not pages:
            await self.documents.mark_status(doc, DocumentStatus.FAILED, error_message="text_extraction_failed")
            raise IngestionError("Failed to extract text from document")

        # split and store
        splitter = None
        if RecursiveCharacterTextSplitter is not None:
            splitter = RecursiveCharacterTextSplitter(
                chunk_size=self.settings.chunk_size, chunk_overlap=self.settings.chunk_overlap
            )

        chunk_index = 0
        for page in pages:
            text = page.text or ""
            if not text.strip():
                continue

            chunks = [text]
            if splitter is not None:
                try:
                    chunks = splitter.split_text(text)
                except Exception:
                    chunks = [text]

            offset = 0
            for c in chunks:
                start = text.find(c, offset)
                if start == -1:
                    start = offset
                end = start + len(c)

                await self.chunks.create(
                    document_id=doc.id,
                    chunk_index=chunk_index,
                    page_number=page.page_number,
                    content=c,
                    char_start=start,
                    char_end=end,
                    metadata={"source": doc.original_filename},
                )
                chunk_index += 1
                offset = end

        await self.documents.mark_status(doc, DocumentStatus.READY)
        await self.audit_logs.create(
            actor_user_id=doc.owner_id,
            action="document.ingest_complete",
            entity_type="document",
            entity_id=doc.id,
            details={"chunks_created": chunk_index},
            ip_address=None,
            user_agent=None,
        )
        await self.session.commit()

        try:
            await EmbeddingService(session=self.session, settings=self.settings).embed_chunks_for_document(doc.id)
        except Exception as exc:
            await self.audit_logs.create(
                actor_user_id=doc.owner_id,
                action="document.embedding_failed",
                entity_type="document",
                entity_id=doc.id,
                details={"error": str(exc)},
                ip_address=None,
                user_agent=None,
            )

    def _extract_pages(self, path: Path) -> List[PageText]:
        """Extract per-page text from a PDF using PyMuPDF with pdfplumber fallback.

        This is synchronous to allow easier testing and reuse from background tasks.
        """
        pages: List[PageText] = []

        if fitz is not None:
            try:
                pdf = fitz.open(path)
                for i in range(pdf.page_count):
                    page = pdf.load_page(i)
                    text = page.get_text("text") or ""
                    pages.append(PageText(page_number=i + 1, text=text))
                return pages
            except Exception:
                pages = []

        if pdfplumber is not None:
            try:
                with pdfplumber.open(path) as p:
                    for i, pg in enumerate(p.pages):
                        text = pg.extract_text() or ""
                        pages.append(PageText(page_number=i + 1, text=text))
                return pages
            except Exception:
                return []

        return []
