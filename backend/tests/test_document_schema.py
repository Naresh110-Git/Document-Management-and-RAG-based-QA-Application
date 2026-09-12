from datetime import datetime, timezone
from uuid import UUID, uuid4

from app.schemas.document import DocumentRead


def test_document_read_schema_accepts_timestamped_document():
    payload = {
        "id": str(uuid4()),
        "title": "Test Document",
        "original_filename": "test.pdf",
        "content_type": "application/pdf",
        "file_size": 1024,
        "page_count": 2,
        "status": "ready",
        "created_at": datetime.now(tz=timezone.utc).isoformat(),
        "updated_at": datetime.now(tz=timezone.utc).isoformat(),
    }

    document = DocumentRead.model_validate(payload)

    assert document.id == UUID(payload["id"])
    assert document.title == "Test Document"
    assert document.page_count == 2
    assert document.status == "ready"
    assert document.created_at.tzinfo is not None
    assert document.updated_at.tzinfo is not None
