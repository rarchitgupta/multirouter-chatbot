import asyncio
import logging

import redis.asyncio as aioredis

from app.config import settings
from app.database import AsyncSessionLocal
from app.ingestion.processor import process_log_entry

logger = logging.getLogger(__name__)

_CONSUMER_NAME = "consumer-1"


class IngestionConsumer:
    """
    Background asyncio task that reads from the Redis Stream consumer group,
    processes each inference log entry, and ACKs on success.

    Unacknowledged messages stay in the PEL (Pending Entry List) and are
    reclaimed for retry after ingestion_retry_after_ms.
    """

    def __init__(self) -> None:
        self._client: aioredis.Redis | None = None
        self._task: asyncio.Task | None = None

    async def start(self) -> None:
        self._client = aioredis.from_url(settings.redis_url, decode_responses=True)
        await self._ensure_group()
        self._task = asyncio.create_task(self._run(), name="ingestion-consumer")
        logger.info("Ingestion consumer started (group=%s)", settings.ingestion_consumer_group)

    async def stop(self) -> None:
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        if self._client:
            await self._client.aclose()
        logger.info("Ingestion consumer stopped")

    async def _ensure_group(self) -> None:
        """Create the consumer group if it doesn't already exist."""
        try:
            await self._client.xgroup_create(
                settings.redis_stream_name,
                settings.ingestion_consumer_group,
                id="0",         # start from the beginning of the stream
                mkstream=True,  # create the stream key if it doesn't exist yet
            )
        except aioredis.ResponseError as e:
            if "BUSYGROUP" not in str(e):
                raise

    async def _run(self) -> None:
        """Main loop: drain PEL retries first, then read new messages."""
        while True:
            try:
                await self._reclaim_pending()
                await self._read_new()
            except asyncio.CancelledError:
                raise
            except Exception as e:
                logger.exception("Consumer loop error: %s", e)
                await asyncio.sleep(1)

    async def _read_new(self) -> None:
        """Read undelivered messages from the stream (blocks up to 1 s)."""
        results = await self._client.xreadgroup(
            groupname=settings.ingestion_consumer_group,
            consumername=_CONSUMER_NAME,
            streams={settings.redis_stream_name: ">"},  # ">" = only new messages
            count=10,
            block=1000,  # ms — yields control back to the event loop each second
        )
        if not results:
            return
        for _stream_name, messages in results:
            for msg_id, fields in messages:
                await self._handle(msg_id, fields)

    async def _reclaim_pending(self) -> None:
        """Reclaim PEL entries idle longer than ingestion_retry_after_ms."""
        try:
            next_id, messages, _deleted = await self._client.xautoclaim(
                name=settings.redis_stream_name,
                groupname=settings.ingestion_consumer_group,
                consumername=_CONSUMER_NAME,
                min_idle_time=settings.ingestion_retry_after_ms,
                start_id="0-0",
                count=10,
            )
            for msg_id, fields in messages:
                await self._handle(msg_id, fields)
        except Exception as e:
            logger.warning("PEL reclaim failed (non-critical): %s", e)

    async def _handle(self, msg_id: str, fields: dict[str, str]) -> None:
        try:
            async with AsyncSessionLocal() as db:
                await process_log_entry(db, fields)
            await self._client.xack(
                settings.redis_stream_name,
                settings.ingestion_consumer_group,
                msg_id,
            )
        except Exception as e:
            # Leave the message in the PEL — _reclaim_pending will retry it.
            logger.error("Failed to process message %s: %s", msg_id, e)


consumer = IngestionConsumer()
