"""Health response schemas."""

from pydantic import BaseModel, ConfigDict


class HealthResponse(BaseModel):
    """Health-check response payload."""

    model_config = ConfigDict(extra="forbid")

    status: str
    service: str
    version: str
    environment: str
