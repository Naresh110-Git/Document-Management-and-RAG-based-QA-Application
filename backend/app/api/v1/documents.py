from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status

from app.api.dependencies.auth import CurrentUser
from app.api.dependencies.services import DocumentServiceDependency
from app.models.user import User
from app.schemas.document import (
    DocumentListResponse,
    DocumentSelectionResponse,
    DocumentUpdateRequest,
    DocumentRead,
)

router = APIRouter(prefix="/documents", tags=["Documents"])


@router.post("/upload", response_model=DocumentRead, status_code=status.HTTP_201_CREATED)
async def upload_document(
    current_user: CurrentUser,
    document_service: DocumentServiceDependency,
    file: UploadFile = File(...),
) -> DocumentRead:
    """Upload a new document for processing."""
    doc = await document_service.upload_document(current_user, file)
    return DocumentRead.model_validate(doc)


@router.get("/", response_model=DocumentListResponse)
async def list_documents(
    current_user: CurrentUser,
    document_service: DocumentServiceDependency,
) -> DocumentListResponse:
    """List documents available to the current user."""
    docs = await document_service.list_documents(current_user)
    return DocumentListResponse(documents=docs)


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    document_id: UUID,
    current_user: CurrentUser,
    document_service: DocumentServiceDependency,
) -> None:
    """Delete a document and its associated embeddings."""
    await document_service.delete_document(current_user, document_id)


@router.put("/{document_id}")
async def update_document(
    document_id: UUID,
    payload: DocumentUpdateRequest,
    current_user: CurrentUser,
    document_service: DocumentServiceDependency,
) -> dict[str, str]:
    """Update document metadata."""
    await document_service.update_document(current_user, document_id, payload)
    return {"status": "updated"}


@router.post("/select", response_model=DocumentSelectionResponse)
async def select_documents(
    payload: DocumentSelectionResponse,
    current_user: CurrentUser,
    document_service: DocumentServiceDependency,
) -> DocumentSelectionResponse:
    """Select documents for RAG-based retrieval."""
    return await document_service.select_documents(current_user, payload)


@router.post("/reindex", status_code=status.HTTP_202_ACCEPTED)
async def reindex_documents(
    current_user: CurrentUser,
    document_service: DocumentServiceDependency,
) -> dict[str, str]:
    """Rebuild document embeddings for the current user."""
    await document_service.reindex_documents(current_user)
    return {"status": "reindex_accepted"}
