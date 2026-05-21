from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, field_validator


class SendMessageRequest(BaseModel):
    content: str

    @field_validator("content")
    @classmethod
    def content_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("content must not be empty")
        return v.strip()


class MessageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    conversation_id: UUID
    role: str
    content: str
    sequence_number: int
    created_at: datetime


class TokenUsage(BaseModel):
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    total_tokens: int | None = None


class SendMessageResponse(BaseModel):
    message: MessageResponse
    usage: TokenUsage | None = None
    latency_ms: int | None = None
