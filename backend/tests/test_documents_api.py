from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID, uuid4

from fastapi.testclient import TestClient

from app.main import create_app

@dataclass
class FakeUser:
    email: str
    id: UUID = uuid4()
    role: str = "user"
    is_active: bool = True


class FakeDocumentService:
    async def upload_document(self, user, file):
        class Doc:
            id = uuid4()
            title = file.filename
            original_filename = file.filename
            content_type = file.content_type
            file_size = 123
            page_count = 1
            status = "ready"
            created_at = datetime.now(tz=UTC)
            updated_at = datetime.now(tz=UTC)
        return Doc()

    async def list_documents(self, user):
        return []

    async def delete_document(self, user, document_id):
        return None

    async def update_document(self, user, document_id, payload):
        return None

    async def select_documents(self, user, payload):
        return {"document_ids": payload.document_ids}


    async def reindex_documents(self, user):
        return None


def build_client(current_user: FakeUser | None = None):
    app = create_app()
    from app.api.dependencies.auth import get_current_active_user
    from app.api.dependencies.services import get_document_service

    app.dependency_overrides[get_document_service] = lambda: FakeDocumentService()
    if current_user is not None:
        app.dependency_overrides[get_current_active_user] = lambda: current_user
    return TestClient(app)


def test_upload_endpoint_returns_created(tmp_path):
    client = build_client(current_user=FakeUser(email="me@example.com"))
    file_path = tmp_path / "doc.pdf"
    file_path.write_bytes(b"%PDF-1.4 test")

    with open(file_path, "rb") as f:
        response = client.post("/api/v1/documents/upload", files={"file": ("doc.pdf", f, "application/pdf")})

    assert response.status_code in (200, 201)


def test_list_documents_endpoint():
    client = build_client(current_user=FakeUser(email="me@example.com"))
    response = client.get("/api/v1/documents/")
    assert response.status_code == 200
    assert "documents" in response.json()


def test_update_document_endpoint():
    client = build_client(current_user=FakeUser(email="me@example.com"))
    doc_id = uuid4()
    response = client.put(f"/api/v1/documents/{doc_id}", json={"title": "Updated Title"})
    assert response.status_code == 200
    assert response.json()["status"] == "updated"


def test_delete_document_endpoint():
    client = build_client(current_user=FakeUser(email="me@example.com"))
    doc_id = uuid4()
    response = client.delete(f"/api/v1/documents/{doc_id}")
    assert response.status_code == 204


def test_select_documents_endpoint():
    client = build_client(current_user=FakeUser(email="me@example.com"))
    doc_id = str(uuid4())
    response = client.post("/api/v1/documents/select", json={"document_ids": [doc_id]})
    assert response.status_code == 200
    assert doc_id in response.json()["document_ids"]


def test_reindex_documents_endpoint():
    client = build_client(current_user=FakeUser(email="me@example.com"))
    response = client.post("/api/v1/documents/reindex")
    assert response.status_code == 202
    assert response.json()["status"] == "reindex_accepted"
