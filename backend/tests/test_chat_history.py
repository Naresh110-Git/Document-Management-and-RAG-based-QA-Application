from uuid import uuid4
from fastapi.testclient import TestClient

from app.main import create_app


class FakeUser:
    def __init__(self, email: str):
        self.email = email
        self.id = uuid4()
        self.role = "user"
        self.is_active = True


class FakeChatService:
    async def ask_question(self, user, payload):
        from app.schemas.chat import ChatHistoryResponse

        return ChatHistoryResponse(
            id=uuid4(),
            question=payload.question,
            answer="Test answer",
            sources=[{"document": "doc.pdf", "page": 1, "chunk": "This is test."}],
            provider="ollama",
            model_name="llama3.1",
            latency_ms=10,
            created_at="2026-01-01T00:00:00Z",
            updated_at="2026-01-01T00:00:00Z",
        )

    async def get_history(self, user):
        from app.schemas.chat import ChatHistoryResponse

        return [
            ChatHistoryResponse(
                id=uuid4(),
                question="What is this?",
                answer="Test answer",
                sources=[{"document": "doc.pdf", "page": 1, "chunk": "This is test."}],
                provider="ollama",
                model_name="llama3.1",
                latency_ms=10,
                created_at="2026-01-01T00:00:00Z",
                updated_at="2026-01-01T00:00:00Z",
            )
        ]

    async def stream_question(self, user, payload):
        yield "Streaming "
        yield "answer"

    async def clear_history(self, user):
        return None


def build_client(current_user=None):
    app = create_app()
    from app.api.dependencies.auth import get_current_active_user
    from app.api.dependencies.services import get_chat_service

    app.dependency_overrides[get_chat_service] = lambda: FakeChatService()
    if current_user is not None:
        app.dependency_overrides[get_current_active_user] = lambda: current_user
    return TestClient(app)


def test_chat_history_endpoint_returns_list():
    client = build_client(current_user=FakeUser(email="me@example.com"))
    response = client.get("/api/v1/chat/history")

    assert response.status_code == 200
    assert isinstance(response.json(), list)
    assert response.json()[0]["question"] == "What is this?"


def test_chat_ask_endpoint():
    client = build_client(current_user=FakeUser(email="me@example.com"))
    response = client.post("/api/v1/chat/", json={"question": "What is the document about?"})

    assert response.status_code == 200
    data = response.json()
    assert data["answer"] == "Test answer"
    assert len(data["sources"]) == 1


def test_chat_stream_endpoint():
    client = build_client(current_user=FakeUser(email="me@example.com"))
    response = client.post("/api/v1/chat/stream", json={"question": "Stream this"})

    assert response.status_code == 200
    assert "text/event-stream" in response.headers["content-type"]
    assert "data:" in response.text
    assert "[DONE]" in response.text


def test_clear_chat_history_endpoint():
    client = build_client(current_user=FakeUser(email="me@example.com"))
    response = client.delete("/api/v1/chat/history")

    assert response.status_code == 204
