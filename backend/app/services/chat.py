from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.models.user import User
from app.schemas.chat import ChatHistoryResponse, ChatRequest


class ChatService:
    """Question answering and chat history business logic."""

    def __init__(self, *, session: AsyncSession, settings: Settings) -> None:
        self.session = session
        self.settings = settings

    async def ask_question(self, user: User, payload: ChatRequest) -> ChatHistoryResponse:
        raise NotImplementedError

    async def stream_question(self, user: User, payload: ChatRequest):
        raise NotImplementedError
        yield ""  # pragma: no cover

    async def get_history(self, user: User) -> list[ChatHistoryResponse]:
        raise NotImplementedError

    async def clear_history(self, user: User) -> None:
        raise NotImplementedError
