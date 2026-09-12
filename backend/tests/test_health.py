"""Health endpoint tests."""

from fastapi.testclient import TestClient

from app.main import create_app


def test_health_check_returns_service_metadata() -> None:
    client = TestClient(create_app())

    response = client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["service"] == "Document Management RAG API"
