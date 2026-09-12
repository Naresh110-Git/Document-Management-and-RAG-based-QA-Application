import os
import pytest
from fastapi.testclient import TestClient

# Ensure tests use an in-memory SQLite DB so they don't require Postgres.
# Set this before importing application modules that create the DB engine.
DB_FILE = "test_chat_history_db.sqlite"
os.environ.setdefault("DATABASE_URL", f"sqlite+aiosqlite:///{DB_FILE}")
os.environ.setdefault("ENVIRONMENT", "test")

from app.api.dependencies.auth import get_current_active_user
from app.core.config import Settings
from app.database.session import AsyncSessionLocal
from app.main import create_app
from app.models.chat import ChatHistory
from app.models.user import User, UserRole


@pytest.mark.asyncio
async def test_chat_history_endpoint_persists_and_returns_rows():
    settings = Settings()
    app = create_app()
    # Ensure DB schema exists for the test by creating all tables on the test DB.
    from app.database.session import engine
    from app.database.base import Base

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as session:
        user = User(
            email="persisted_user@example.com",
            hashed_password="testpass",
            role=UserRole.USER,
            is_active=True,
            is_verified=True,
        )
        session.add(user)
        await session.flush()

        history = ChatHistory(
            user_id=user.id,
            question="What is persistence?",
            answer="Persistence means storing data long term.",
            sources=[{"document": "doc.pdf", "page": 1, "chunk": "Persistent chunk text."}],
            provider="ollama",
            model_name="llama3.1",
            latency_ms=5,
        )
        session.add(history)
        await session.commit()

        app.dependency_overrides[get_current_active_user] = lambda: user

        client = TestClient(app)
        response = client.get("/api/v1/chat/history")

        assert response.status_code == 200
        json_data = response.json()
        assert isinstance(json_data, list)
        assert any(entry["question"] == "What is persistence?" for entry in json_data)

        await session.delete(history)
        await session.delete(user)
        await session.commit()

    # Tear down DB schema and temporary file.
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()
    try:
        os.remove(DB_FILE)
    except OSError:
        pass
