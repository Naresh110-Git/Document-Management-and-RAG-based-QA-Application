from collections.abc import Awaitable, Callable
from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.database.session import get_db
from app.services.chat import ChatService
from app.services.document import DocumentService
from app.services.rag import RAGChatService


async def get_chat_service(
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> ChatService:
    return RAGChatService(session=db, settings=settings)


async def get_document_service(
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> DocumentService:
    return DocumentService(session=db, settings=settings)


ChatServiceDependency = Annotated[ChatService, Depends(get_chat_service)]
DocumentServiceDependency = Annotated[DocumentService, Depends(get_document_service)]
