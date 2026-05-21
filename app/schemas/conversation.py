from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, model_validator


class ConversationCreate(BaseModel):
    model: str
    provider: str

    @model_validator(mode="after")
    def check_provider_model(self) -> "ConversationCreate":
        from app.sdk.providers import validate_provider_model
        validate_provider_model(self.provider, self.model)
        return self


class ConversationUpdate(BaseModel):
    status: str

    @model_validator(mode="after")
    def check_status(self) -> "ConversationUpdate":
        allowed = {"active", "cancelled", "completed"}
        if self.status not in allowed:
            raise ValueError(f"status must be one of: {sorted(allowed)}")
        return self


class ConversationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str | None
    status: str
    model: str
    provider: str
    created_at: datetime
    updated_at: datetime
