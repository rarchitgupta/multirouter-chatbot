from collections.abc import AsyncIterator
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.sse import EventSourceResponse, ServerSentEvent
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.schemas.conversation import ConversationCreate, ConversationResponse, ConversationUpdate
from app.schemas.message import MessageResponse, SendMessageRequest, SendMessageResponse, TokenUsage
from app.sdk.providers import SUPPORTED_MODELS
from app.sdk.wrapper import (
    LLMAuthError,
    LLMContextError,
    LLMError,
    LLMProviderError,
    LLMRateLimitError,
    llm_wrapper,
)
from app.ingestion.publisher import publisher
from app.services import conversation as conversation_service
from app.services import message as message_service

router = APIRouter()


# ---------------------------------------------------------------------------
# Providers
# ---------------------------------------------------------------------------

@router.get("/providers")
async def list_providers():
    """Return providers that have an API key configured, with their model lists."""
    available: dict[str, list[str]] = {}
    if settings.anthropic_api_key:
        available["anthropic"] = SUPPORTED_MODELS["anthropic"]
    if settings.openai_api_key:
        available["openai"] = SUPPORTED_MODELS["openai"]
    if settings.gemini_api_key:
        available["gemini"] = SUPPORTED_MODELS["gemini"]
    return {"providers": available}


# ---------------------------------------------------------------------------
# Conversations
# ---------------------------------------------------------------------------

@router.post("/conversations", response_model=ConversationResponse, status_code=201)
async def create_conversation(
    body: ConversationCreate,
    db: AsyncSession = Depends(get_db),
):
    return await conversation_service.create_conversation(db, provider=body.provider, model=body.model)


@router.get("/conversations", response_model=list[ConversationResponse])
async def list_conversations(
    status: str | None = Query(None, description="Filter by status: active, cancelled, completed"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    return await conversation_service.list_conversations(db, status=status, limit=limit, offset=offset)


@router.get("/conversations/{conversation_id}", response_model=ConversationResponse)
async def get_conversation(
    conversation_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    conversation = await conversation_service.get_conversation(db, conversation_id)
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conversation


@router.patch("/conversations/{conversation_id}", response_model=ConversationResponse)
async def update_conversation(
    conversation_id: UUID,
    body: ConversationUpdate,
    db: AsyncSession = Depends(get_db),
):
    conversation = await conversation_service.update_conversation(db, conversation_id, status=body.status)
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conversation


@router.delete("/conversations/{conversation_id}", status_code=204)
async def delete_conversation(
    conversation_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    deleted = await conversation_service.delete_conversation(db, conversation_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Conversation not found")


# ---------------------------------------------------------------------------
# Messages
# ---------------------------------------------------------------------------

@router.get("/conversations/{conversation_id}/messages", response_model=list[MessageResponse])
async def list_messages(
    conversation_id: UUID,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    conversation = await conversation_service.get_conversation(db, conversation_id)
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return await message_service.get_messages(db, conversation_id, limit=limit, offset=offset)


@router.post("/conversations/{conversation_id}/messages", response_class=EventSourceResponse)
async def send_message(
    conversation_id: UUID,
    body: SendMessageRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> AsyncIterator[ServerSentEvent]:
    """
    Stream the assistant reply as Server-Sent Events.

    Event types:
      delta  — {"type": "delta", "content": "<chunk>"}
      done   — {"type": "done",  "message_id": "...", "usage": {...}, "latency_ms": ...}
      error  — {"type": "error", "message": "..."}
    """
    conversation = await conversation_service.get_conversation(db, conversation_id)
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    if conversation.status != "active":
        raise HTTPException(
            status_code=409,
            detail=f"Cannot send message to a {conversation.status} conversation",
        )

    history = await message_service.get_recent_messages(
        db, conversation_id, limit=settings.max_conversation_history
    )

    await message_service.create_message(db, conversation_id, role="user", content=body.content)

    if conversation.title is None:
        await conversation_service.update_conversation(db, conversation_id, title=body.content[:60])

    llm_messages = [{"role": m.role, "content": m.content} for m in history]
    llm_messages.append({"role": "user", "content": body.content})

    try:
        chat_stream = await llm_wrapper.stream_chat(
            messages=llm_messages,
            model=conversation.model,
            provider=conversation.provider,
        )
    except LLMError as e:
        await publisher.publish({
            "conversation_id": conversation_id,
            "model": conversation.model,
            "provider": conversation.provider,
            "status": "error",
            "latency_ms": e.latency_ms,
            "input_preview": body.content[:200],
            "request_at": e.request_at,
        })
        if isinstance(e, LLMAuthError):
            raise HTTPException(status_code=401, detail=str(e))
        if isinstance(e, LLMRateLimitError):
            raise HTTPException(status_code=429, detail=str(e))
        if isinstance(e, LLMContextError):
            raise HTTPException(status_code=422, detail=str(e))
        raise HTTPException(status_code=502, detail=str(e))

    try:
        async for chunk in chat_stream:
            if await request.is_disconnected():
                return
            yield ServerSentEvent(
                event="delta",
                data={"type": "delta", "content": chunk},
            )
    except LLMError as e:
        await publisher.publish({
            "conversation_id": conversation_id,
            "model": conversation.model,
            "provider": conversation.provider,
            "status": "error",
            "latency_ms": e.latency_ms,
            "input_preview": body.content[:200],
            "request_at": e.request_at,
        })
        yield ServerSentEvent(event="error", data={"type": "error", "message": str(e)})
        return
    except Exception as e:
        yield ServerSentEvent(event="error", data={"type": "error", "message": f"Unexpected error: {e}"})
        return

    result = chat_stream.result
    assistant_message = await message_service.create_message(
        db, conversation_id, role="assistant", content=result.content
    )

    await publisher.publish({
        "conversation_id": conversation_id,
        "message_id": assistant_message.id,
        "model": conversation.model,
        "provider": conversation.provider,
        "status": "success",
        "latency_ms": result.latency_ms,
        "prompt_tokens": result.prompt_tokens,
        "completion_tokens": result.completion_tokens,
        "total_tokens": result.total_tokens,
        "input_preview": body.content[:200],
        "output_preview": result.content[:200],
        "request_at": result.request_at,
        "response_at": result.response_at,
    })

    yield ServerSentEvent(
        event="done",
        data={
            "type": "done",
            "message_id": str(assistant_message.id),
            "usage": {
                "prompt_tokens": result.prompt_tokens,
                "completion_tokens": result.completion_tokens,
                "total_tokens": result.total_tokens,
            },
            "latency_ms": result.latency_ms,
        },
    )
