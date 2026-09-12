from uuid import UUID
import io
import asyncio
from pathlib import Path
from hashlib import sha256
from typing import List

from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.background import background_manager
from app.services.cache import document_cache

from app.core.config import Settings
from app.core.exceptions import AppError, ConflictError, AuthorizationError
from app.models.user import User, UserRole
from app.models.document import Document, DocumentStatus
from app.repositories.document import DocumentRepository
from app.repositories.audit import AuditLogRepository
from app.services.storage import StorageService, StorageError
from app.utils.request import RequestMetadata
from app.services.ingest import IngestionService
from app.services.embeddings import EmbeddingService
from app.database.session import AsyncSessionLocal


class DocumentService:
    """Document management business logic."""

    def __init__(self, *, session: AsyncSession, settings: Settings) -> None:
        self.session = session
        self.settings = settings
        self.documents = DocumentRepository(session)
        self.audit_logs = AuditLogRepository(session)
        self.storage = StorageService(settings)

    async def upload_document(self, user: User, file: UploadFile) -> Document:
        """Validate and persist an uploaded PDF file and create a Document record."""
        if file.content_type not in self.settings.allowed_upload_types:
            raise AppError("Unsupported file type", status_code=400)

        # Save file to disk
        try:
            stored_filename, path, size, checksum = await self.storage.save_upload(str(user.id), file)
        except StorageError as exc:
            raise AppError(str(exc), status_code=400) from exc

        # Try to determine page count
        page_count = None
        try:
            import fitz

            pdf_doc = fitz.open(stream=path.read_bytes(), filetype="pdf")
            page_count = pdf_doc.page_count
        except Exception:
            try:
                import pdfplumber

                with pdfplumber.open(path) as p:
                    page_count = len(p.pages)
            except Exception:
                page_count = None

        doc = await self.documents.create(
            owner_id=user.id,
            title=file.filename,
            original_filename=file.filename,
            stored_filename=stored_filename,
            storage_path=str(path),
            content_type=file.content_type or "application/octet-stream",
            file_size=size,
            checksum_sha256=checksum,
            page_count=page_count,
        )

        await self.audit_logs.create(
            actor_user_id=user.id,
            action="document.upload",
            entity_type="document",
            entity_id=doc.id,
            details={"original_filename": file.filename, "stored_filename": stored_filename},
            ip_address=None,
            user_agent=None,
        )

        await self.session.commit()
        await self.session.refresh(doc)
        await document_cache.delete(f"documents:{user.id}")

        # schedule ingestion in background using a new DB session
        async def _background_ingest(doc_id: UUID) -> None:
            async with AsyncSessionLocal() as new_session:
                try:
                    await IngestionService(session=new_session, settings=self.settings).process_document(doc_id)
                except Exception:
                    # ingestion errors are logged via audit logs inside service
                    return

        try:
            background_manager.submit(_background_ingest(doc.id))
        except RuntimeError:
            # If event loop isn't running, skip background scheduling
            asyncio.create_task(_background_ingest(doc.id))

        return doc

    async def list_documents(self, user: User) -> List[Document]:
        """Return documents belonging to the user."""
        cache_key = f"documents:{user.id}"
        cached = await document_cache.get(cache_key)
        if cached is not None:
            return cached
        documents = await self.documents.list_by_owner(user.id)
        await document_cache.set(cache_key, documents)
        return documents

    async def delete_document(self, user: User, document_id: UUID) -> None:
        """Delete a document if the user is the owner or admin."""
        doc = await self.documents.get_by_id(document_id)
        if doc is None:
            raise AppError("Document not found", status_code=404)

        # Authorization
        if doc.owner_id != user.id and (not (isinstance(user.role, UserRole) and user.role == UserRole.ADMIN)):
            raise AuthorizationError("Insufficient permissions to delete document")

        owner_id = doc.owner_id

        # delete file
        try:
            await self.storage.delete_file(Path(doc.storage_path))
        except Exception:
            pass

        await self.documents.delete(doc)
        await self.audit_logs.create(
            actor_user_id=user.id,
            action="document.delete",
            entity_type="document",
            entity_id=doc.id,
            details={"stored_filename": doc.stored_filename},
            ip_address=None,
            user_agent=None,
        )
        await self.session.commit()
        await document_cache.delete(f"documents:{owner_id}")

    async def update_document(self, user: User, document_id: UUID, payload) -> None:
        """Update editable document metadata (title)."""
        doc = await self.documents.get_by_id(document_id)
        if doc is None:
            raise AppError("Document not found", status_code=404)

        if doc.owner_id != user.id and (not (isinstance(user.role, UserRole) and user.role == UserRole.ADMIN)):
            raise AuthorizationError("Insufficient permissions to update document")

        await self.documents.update_title(doc, payload.title)
        await self.audit_logs.create(
            actor_user_id=user.id,
            action="document.update",
            entity_type="document",
            entity_id=doc.id,
            details={"title": payload.title},
            ip_address=None,
            user_agent=None,
        )
        await self.session.commit()
        await document_cache.delete(f"documents:{doc.owner_id}")

    async def select_documents(self, user: User, payload) -> object:
        """Validate a selection of documents belong to the user and return the selection."""
        selected = []
        for doc_id in payload.document_ids:
            doc = await self.documents.get_by_id(doc_id)
            if doc is None:
                raise AppError(f"Document {doc_id} not found", status_code=404)
            if doc.owner_id != user.id and (not (isinstance(user.role, UserRole) and user.role == UserRole.ADMIN)):
                raise AuthorizationError("Insufficient permissions to select document")
            selected.append(doc_id)
        return {"document_ids": selected}

    async def reindex_documents(self, user: User) -> None:
        """Rebuild embeddings for the user's documents."""
        documents = await self.documents.list_by_owner(user.id)
        total_embeddings = 0
        for doc in documents:
            total_embeddings += await EmbeddingService(session=self.session, settings=self.settings).embed_chunks_for_document(doc.id)

        await self.audit_logs.create(
            actor_user_id=user.id,
            action="document.reindex",
            entity_type="user",
            entity_id=user.id,
            details={"documents_reindexed": len(documents), "embeddings_created": total_embeddings},
            ip_address=None,
            user_agent=None,
        )
        await self.session.commit()
