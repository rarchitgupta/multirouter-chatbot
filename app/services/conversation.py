import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.conversation import Conversation


async def create_conversation(
    db: AsyncSession,
    provider: str,
    model: str,
) -> Conversation:
    conversation = Conversation(
        id=uuid.uuid4(),
        provider=provider,
        model=model,
        status="active",
        title=None,
    )
    db.add(conversation)
    await db.commit()
    await db.refresh(conversation)
    return conversation


async def get_conversation(
    db: AsyncSession,
    conversation_id: uuid.UUID,
) -> Conversation | None:
    result = await db.execute(
        select(Conversation).where(Conversation.id == conversation_id)
    )
    return result.scalar_one_or_none()


async def list_conversations(
    db: AsyncSession,
    status: str | None = None,
    limit: int = 20,
    offset: int = 0,
) -> list[Conversation]:
    query = (
        select(Conversation)
        .order_by(Conversation.updated_at.desc())
        .limit(limit)
        .offset(offset)
    )
    if status is not None:
        query = query.where(Conversation.status == status)
    result = await db.execute(query)
    return list(result.scalars().all())


async def update_conversation(
    db: AsyncSession,
    conversation_id: uuid.UUID,
    **kwargs,
) -> Conversation | None:
    conversation = await get_conversation(db, conversation_id)
    if conversation is None:
        return None
    for key, value in kwargs.items():
        setattr(conversation, key, value)
    # Explicitly stamp updated_at since SQLAlchemy's onupdate only fires
    # when a tracked column changes — kwargs may only contain non-mapped fields.
    conversation.updated_at = datetime.now(UTC)
    await db.commit()
    await db.refresh(conversation)
    return conversation


async def delete_conversation(
    db: AsyncSession,
    conversation_id: uuid.UUID,
) -> bool:
    conversation = await get_conversation(db, conversation_id)
    if conversation is None:
        return False
    await db.delete(conversation)
    await db.commit()
    return True
