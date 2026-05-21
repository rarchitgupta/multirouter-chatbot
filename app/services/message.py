import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.message import Message


async def _next_sequence_number(db: AsyncSession, conversation_id: uuid.UUID) -> int:
    result = await db.execute(
        select(func.coalesce(func.max(Message.sequence_number), 0)).where(
            Message.conversation_id == conversation_id
        )
    )
    return result.scalar_one() + 1


async def create_message(
    db: AsyncSession,
    conversation_id: uuid.UUID,
    role: str,
    content: str,
) -> Message:
    sequence_number = await _next_sequence_number(db, conversation_id)
    message = Message(
        id=uuid.uuid4(),
        conversation_id=conversation_id,
        role=role,
        content=content,
        sequence_number=sequence_number,
    )
    db.add(message)
    await db.commit()
    await db.refresh(message)
    return message


async def get_messages(
    db: AsyncSession,
    conversation_id: uuid.UUID,
    limit: int = 50,
    offset: int = 0,
) -> list[Message]:
    """Return messages in chronological order for the list endpoint."""
    result = await db.execute(
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.sequence_number.asc())
        .limit(limit)
        .offset(offset)
    )
    return list(result.scalars().all())


async def get_recent_messages(
    db: AsyncSession,
    conversation_id: uuid.UUID,
    limit: int = 20,
) -> list[Message]:
    """
    Return the most recent `limit` messages in chronological order.
    Used to build the context window for LLM calls — we want the tail of the
    history, not the head, so we fetch DESC and reverse.
    """
    result = await db.execute(
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.sequence_number.desc())
        .limit(limit)
    )
    messages = list(result.scalars().all())
    return list(reversed(messages))
