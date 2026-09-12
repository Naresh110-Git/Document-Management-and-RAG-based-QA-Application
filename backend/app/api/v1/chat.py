import json
from collections.abc import AsyncIterator
from fastapi import APIRouter, Depends, status
from fastapi.responses import StreamingResponse

from app.api.dependencies.auth import CurrentUser
from app.api.dependencies.services import ChatServiceDependency
from app.schemas.chat import ChatHistoryResponse, ChatRequest

router = APIRouter(prefix="/chat", tags=["Chat"])


@router.post("", response_model=ChatHistoryResponse, include_in_schema=False)
@router.post("/", response_model=ChatHistoryResponse)
@router.post("/ask", response_model=ChatHistoryResponse)
async def chat(
    payload: ChatRequest,
    current_user: CurrentUser,
    chat_service: ChatServiceDependency,
) -> ChatHistoryResponse:
    """Submit a question and retrieve a RAG answer."""
    return await chat_service.ask_question(current_user, payload)


@router.post("/stream")
async def chat_stream(
    payload: ChatRequest,
    current_user: CurrentUser,
    chat_service: ChatServiceDependency,
) -> StreamingResponse:
    """Stream a RAG answer back to the client as server-sent events."""
    async def event_generator() -> AsyncIterator[str]:
        async for chunk in chat_service.stream_question(current_user, payload):
            yield f"data: {json.dumps({'chunk': chunk})}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.get("/history", response_model=list[ChatHistoryResponse])
async def chat_history(
    current_user: CurrentUser,
    chat_service: ChatServiceDependency,
) -> list[ChatHistoryResponse]:
    """Retrieve the user's chat history."""
    return await chat_service.get_history(current_user)


@router.delete("/history", status_code=status.HTTP_204_NO_CONTENT)
async def clear_history(
    current_user: CurrentUser,
    chat_service: ChatServiceDependency,
) -> None:
    """Delete chat history for the authenticated user."""
    await chat_service.clear_history(current_user)
