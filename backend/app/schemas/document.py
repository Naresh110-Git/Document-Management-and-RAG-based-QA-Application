from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class DocumentRead(BaseModel):
    """Document metadata returned in list responses."""

    model_config = ConfigDict(from_attributes=True, extra="forbid")

    id: UUID
    title: str
    original_filename: str
    content_type: str
    file_size: int
    page_count: int | None
    status: str
    created_at: datetime
    updated_at: datetime



class DocumentListResponse(BaseModel):
    """Document list response payload."""

    model_config = ConfigDict(extra="forbid")

    documents: list[DocumentRead]


class DocumentUpdateRequest(BaseModel):
    """Payload to update document metadata."""

    model_config = ConfigDict(extra="forbid")

    title: str = Field(..., max_length=255)


class DocumentSelectionResponse(BaseModel):
    """Selected documents payload for RAG queries."""

    model_config = ConfigDict(extra="forbid")

    document_ids: list[UUID]
