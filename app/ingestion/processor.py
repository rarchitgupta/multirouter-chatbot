import logging
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, field_validator
from sqlalchemy.ext.asyncio import AsyncSession

from app.ingestion.pii import redact
from app.models.inference_log import InferenceLog

logger = logging.getLogger(__name__)


class InferenceLogPayload(BaseModel):
    """Pydantic schema for deserializing the Redis Stream message fields.

    All fields arrive as strings from Redis; validators coerce types back.
    Optional fields are absent when None was skipped in the publisher.
    """

    conversation_id: UUID
    message_id: UUID | None = None
    model: str
    provider: str
    status: str
    latency_ms: int | None = None
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    total_tokens: int | None = None
    input_preview: str | None = None
    output_preview: str | None = None
    request_at: datetime
    response_at: datetime | None = None

    @field_validator("latency_ms", "prompt_tokens", "completion_tokens", "total_tokens", mode="before")
    @classmethod
    def coerce_int(cls, v: str | None) -> int | None:
        if v == "" or v is None:
            return None
        return int(v)


async def process_log_entry(db: AsyncSession, fields: dict[str, str]) -> None:
    """Validate, PII-redact previews, and write one inference log row."""
    payload = InferenceLogPayload.model_validate(fields)

    log = InferenceLog(
        conversation_id=payload.conversation_id,
        message_id=payload.message_id,
        model=payload.model,
        provider=payload.provider,
        status=payload.status,
        latency_ms=payload.latency_ms,
        prompt_tokens=payload.prompt_tokens,
        completion_tokens=payload.completion_tokens,
        total_tokens=payload.total_tokens,
        input_preview=redact(payload.input_preview),
        output_preview=redact(payload.output_preview),
        request_at=payload.request_at,
        response_at=payload.response_at,
    )
    db.add(log)
    await db.commit()
    logger.debug("Inference log written: conversation=%s status=%s", payload.conversation_id, payload.status)
