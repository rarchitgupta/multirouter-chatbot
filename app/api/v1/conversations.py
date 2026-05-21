from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.schemas.conversation import ConversationCreate, ConversationResponse, ConversationUpdate
from app.schemas.message import MessageResponse, SendMessageRequest, SendMessageResponse, TokenUsage
from app.sdk.providers import SUPPORTED_MODELS
from app.sdk.wrapper import (
    LLMAuthError,
    LLMContextError,
    LLMProviderError,
    LLMRateLimitError,
    llm_wrapper,
)
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
    conversation = await conversation_service.create_conversation(
        db, provider=body.provider, model=body.model
    )
    return conversation


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
    conversation = await conversation_service.update_conversation(
        db, conversation_id, status=body.status
    )
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


@router.post("/conversations/{conversation_id}/messages", response_model=SendMessageResponse)
async def send_message(
    conversation_id: UUID,
    body: SendMessageRequest,
    db: AsyncSession = Depends(get_db),
):
    # 1. Validate conversation exists and is active.
    conversation = await conversation_service.get_conversation(db, conversation_id)
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    if conversation.status != "active":
        raise HTTPException(
            status_code=409,
            detail=f"Cannot send message to a {conversation.status} conversation",
        )

    # 2. Fetch recent history BEFORE saving the new user message so we don't
    #    include it twice when building the LLM context.
    history = await message_service.get_recent_messages(
        db, conversation_id, limit=settings.max_conversation_history
    )

    # 3. Persist the user message.
    await message_service.create_message(db, conversation_id, role="user", content=body.content)

    # 4. Derive title from the first user message if not set yet.
    if conversation.title is None:
        await conversation_service.update_conversation(
            db, conversation_id, title=body.content[:60]
        )

    # 5. Build the messages array for LiteLLM — history + new turn.
    llm_messages = [{"role": m.role, "content": m.content} for m in history]
    llm_messages.append({"role": "user", "content": body.content})

    # 6. Call the LLM. Map typed errors to appropriate HTTP status codes.
    try:
        result = await llm_wrapper.chat(
            messages=llm_messages,
            model=conversation.model,
            provider=conversation.provider,
        )
    except LLMAuthError as e:
        raise HTTPException(status_code=401, detail=str(e))
    except LLMRateLimitError as e:
        raise HTTPException(status_code=429, detail=str(e))
    except LLMContextError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except LLMProviderError as e:
        raise HTTPException(status_code=502, detail=str(e))

    # 7. Persist the assistant message.
    assistant_message = await message_service.create_message(
        db, conversation_id, role="assistant", content=result.content
    )

    # Phase 4: publish inference log to Redis here.

    return SendMessageResponse(
        message=MessageResponse.model_validate(assistant_message),
        usage=TokenUsage(
            prompt_tokens=result.prompt_tokens,
            completion_tokens=result.completion_tokens,
            total_tokens=result.total_tokens,
        ),
        latency_ms=result.latency_ms,
    )
