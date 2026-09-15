"""End-to-end integration test for the Document Management and RAG Q&A Application."""

import io
from pathlib import Path
from uuid import uuid4
import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.database.base import Base
from app.database.session import AsyncSessionLocal, engine
from app.main import create_app
from app.models.user import UserRole
from app.services.ingest import IngestionService


def create_minimal_pdf() -> bytes:
    """Create a minimal valid PDF document."""
    try:
        import fitz
        doc = fitz.open()
        page = doc.new_page()
        page.insert_text((72, 72), "FastAPI and RAG provide efficient document Q&A capabilities.")
        return doc.write()
    except Exception:
        return b"%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj 2 0 obj<</Type/Pages/Count 1/Kids[3 0 R]>>endobj 3 0 obj<</Type/Page/MediaBox[0 0 612 792]/Parent 2 0 R/Contents 4 0 R>>endobj 4 0 obj<</Length 51>>stream\nBT /F1 12 Tf 72 712 Td (FastAPI and RAG provide document capabilities) Tj ET\nendstream\nendobj\nxref\n0 5\n0000000000 65535 f \n0000000009 00000 n \n0000000052 00000 n \n0000000102 00000 n \n0000000192 00000 n \ntrailer<</Size 5/Root 1 0 R>>\nstartxref\n293\n%%EOF\n"


@pytest.mark.asyncio
async def test_full_rag_workflow(monkeypatch, tmp_path):
    # Setup DB schema
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    app = create_app()

    # Mock embeddings and LLM to be fast and deterministic in tests
    from app.services import embeddings as emb_mod
    from app.services import llm as llm_mod

    class MockEmbeddingModel:
        def encode(self, texts, show_progress_bar=False):
            return [[0.05] * 384 for _ in texts]

    def fake_load_model(self):
        self.model = MockEmbeddingModel()

    monkeypatch.setattr(emb_mod.EmbeddingService, "_load_model", fake_load_model)

    class MockLLMProvider(llm_mod.BaseProvider):
        async def generate(self, prompt: str, max_tokens: int = 512, temperature: float = 0.2) -> str:
            return "FastAPI and RAG provide efficient document Q&A capabilities [doc.pdf 1]."

    monkeypatch.setattr(llm_mod.LLMService, "_build_provider", lambda self: MockLLMProvider(self.settings))

    client = TestClient(app)

    # 1. Register
    email = f"e2e_user_{uuid4().hex[:8]}@example.com"
    password = "StrongPassword123!"
    reg_resp = client.post("/api/v1/register", json={"email": email, "password": password, "full_name": "E2E User"})
    assert reg_resp.status_code == 201
    user_id = reg_resp.json()["id"]

    # 2. Login
    login_resp = client.post("/api/v1/login", json={"email": email, "password": password})
    assert login_resp.status_code == 200
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 3. Profile /me
    me_resp = client.get("/api/v1/me", headers=headers)
    assert me_resp.status_code == 200
    assert me_resp.json()["email"] == email

    # 4. Upload document
    pdf_bytes = create_minimal_pdf()
    upload_resp = client.post(
        "/api/v1/documents/upload",
        headers=headers,
        files={"file": ("doc.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
    )
    assert upload_resp.status_code == 201
    doc_id = upload_resp.json()["id"]

    # 5. List documents
    list_resp = client.get("/api/v1/documents/", headers=headers)
    assert list_resp.status_code == 200
    docs = list_resp.json()["documents"]
    assert any(d["id"] == doc_id for d in docs)

    # 6. Ensure ingestion is completed
    import asyncio
    from uuid import UUID
    from app.models.document import DocumentStatus
    from app.repositories.document import DocumentRepository

    target_uuid = UUID(doc_id)
    for _ in range(50):
        async with AsyncSessionLocal() as session:
            doc_repo = DocumentRepository(session)
            d = await doc_repo.get_by_id(target_uuid)
            if d and d.status == DocumentStatus.READY:
                break
        await asyncio.sleep(0.1)
    else:
        async with AsyncSessionLocal() as session:
            settings = Settings()
            ingest_svc = IngestionService(session=session, settings=settings)
            await ingest_svc.process_document(target_uuid)

    # 7. Ask question via RAG
    chat_resp = client.post(
        "/api/v1/chat/",
        headers=headers,
        json={"question": "What does FastAPI and RAG provide?", "document_ids": [doc_id]},
    )
    assert chat_resp.status_code == 200
    chat_data = chat_resp.json()
    assert "FastAPI and RAG provide" in chat_data["answer"]
    assert chat_data["sources"] is not None

    # 8. Stream question
    stream_resp = client.post(
        "/api/v1/chat/stream",
        headers=headers,
        json={"question": "What does FastAPI and RAG provide?", "document_ids": [doc_id]},
    )
    assert stream_resp.status_code == 200
    assert "text/event-stream" in stream_resp.headers["content-type"]
    assert "data:" in stream_resp.text
    stream_resp.close()

    # 9. Verify history
    hist_resp = client.get("/api/v1/chat/history", headers=headers)
    assert hist_resp.status_code == 200
    assert len(hist_resp.json()) >= 1

    # 10. Clear history
    del_hist_resp = client.delete("/api/v1/chat/history", headers=headers)
    assert del_hist_resp.status_code == 204

    hist_resp2 = client.get("/api/v1/chat/history", headers=headers)
    assert hist_resp2.status_code == 200
    assert len(hist_resp2.json()) == 0

    # 11. Delete document
    del_doc_resp = client.delete(f"/api/v1/documents/{doc_id}", headers=headers)
    assert del_doc_resp.status_code == 204

    client.close()

    # Allow pending async operations to settle before teardown
    await asyncio.sleep(0.2)

    # Teardown DB tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()
