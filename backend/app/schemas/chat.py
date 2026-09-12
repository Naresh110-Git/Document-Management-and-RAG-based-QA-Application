from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ChatRequest(BaseModel):
    """Payload for a chat question."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    question: str | None = Field(default=None, max_length=2000)
    query: str | None = Field(default=None, max_length=2000)
    document_ids: list[UUID] | None = None

    @model_validator(mode="after")
    def populate_question(self) -> "ChatRequest":
        if not self.question and self.query:
            self.question = self.query
        elif not self.question and not self.query:
            raise ValueError("Either 'question' or 'query' must be provided.")
        return self


class ChatSource(BaseModel):
    """Source metadata for a RAG response."""

    model_config = ConfigDict(extra="forbid")

    document: str
    page: int | None = None
    chunk: str


class ChatHistoryResponse(BaseModel):
    """Chat history entry returned to the client."""

    model_config = ConfigDict(from_attributes=True, extra="forbid")

    id: UUID
    question: str
    answer: str
    sources: list[ChatSource] | None
    provider: str | None
    model_name: str | None
    latency_ms: int | None
    created_at: datetime
    updated_at: datetime
