from datetime import UTC, datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.services import analytics as analytics_service

router = APIRouter()


@router.get("/analytics/overview")
async def get_overview(db: AsyncSession = Depends(get_db)):
    """All-time summary: conversations, messages, tokens, avg latency, error rate."""
    return await analytics_service.get_overview(db)


@router.get("/analytics/latency")
async def get_latency(
    from_dt: Annotated[datetime, Query(alias="from")] = None,
    to_dt: Annotated[datetime, Query(alias="to")] = None,
    bucket: Annotated[str, Query(description="minute | hour | day")] = "hour",
    provider: str | None = None,
    model: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    """P50/P90/P99 latency with time-bucketed breakdown."""
    now = datetime.now(UTC)
    if from_dt is None:
        from_dt = now - timedelta(hours=24)
    if to_dt is None:
        to_dt = now
    return await analytics_service.get_latency(db, from_dt, to_dt, bucket, provider, model)


@router.get("/analytics/throughput")
async def get_throughput(
    from_dt: Annotated[datetime, Query(alias="from")] = None,
    to_dt: Annotated[datetime, Query(alias="to")] = None,
    bucket: Annotated[str, Query(description="minute | hour | day")] = "hour",
    db: AsyncSession = Depends(get_db),
):
    """Request counts and token usage over time."""
    now = datetime.now(UTC)
    if from_dt is None:
        from_dt = now - timedelta(hours=24)
    if to_dt is None:
        to_dt = now
    return await analytics_service.get_throughput(db, from_dt, to_dt, bucket)


@router.get("/analytics/errors")
async def get_errors(
    from_dt: Annotated[datetime, Query(alias="from")] = None,
    to_dt: Annotated[datetime, Query(alias="to")] = None,
    db: AsyncSession = Depends(get_db),
):
    """Error rates broken down by provider and error type."""
    now = datetime.now(UTC)
    if from_dt is None:
        from_dt = now - timedelta(hours=24)
    if to_dt is None:
        to_dt = now
    return await analytics_service.get_errors(db, from_dt, to_dt)
