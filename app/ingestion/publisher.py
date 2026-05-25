import logging
from datetime import datetime
from uuid import UUID

import redis.asyncio as aioredis

from app.config import settings

logger = logging.getLogger(__name__)


class InferenceLogPublisher:
    def __init__(self) -> None:
        self._client: aioredis.Redis | None = None

    async def _ensure_client(self) -> aioredis.Redis:
        if self._client is None:
            self._client = aioredis.from_url(settings.redis_url, decode_responses=True)
        return self._client

    async def close(self) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None

    async def publish(self, payload: dict) -> None:
        """Fire-and-forget XADD. Never raises — a logging failure must not affect the response."""
        try:
            client = await self._ensure_client()
            serialized = _serialize(payload)
            await client.xadd(
                settings.redis_stream_name,
                serialized,
                maxlen=settings.redis_stream_maxlen,
                approximate=True,
            )
        except Exception as e:
            logger.error("Failed to publish inference log to Redis: %s", e)


def _serialize(payload: dict) -> dict[str, str]:
    """Convert a payload dict to Redis-safe string values, skipping None fields."""
    out: dict[str, str] = {}
    for k, v in payload.items():
        if v is None:
            continue
        if isinstance(v, datetime):
            out[k] = v.isoformat()
        elif isinstance(v, UUID):
            out[k] = str(v)
        else:
            out[k] = str(v)
    return out


publisher = InferenceLogPublisher()
