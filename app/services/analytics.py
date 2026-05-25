from datetime import UTC, datetime, timedelta

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

_VALID_BUCKETS = {"minute", "hour", "day"}


def _default_range() -> tuple[datetime, datetime]:
    now = datetime.now(UTC)
    return now - timedelta(hours=24), now


async def get_overview(db: AsyncSession) -> dict:
    row = (
        await db.execute(
            text("""
                SELECT
                    COUNT(*)                                             AS total_requests,
                    COUNT(*) FILTER (WHERE status = 'error')            AS error_count,
                    AVG(latency_ms) FILTER (WHERE status = 'success')   AS avg_latency_ms,
                    COALESCE(SUM(total_tokens), 0)                      AS total_tokens
                FROM inference_logs
            """)
        )
    ).one()

    conv_count = (await db.execute(text("SELECT COUNT(*) FROM conversations"))).scalar()
    msg_count = (await db.execute(text("SELECT COUNT(*) FROM messages"))).scalar()

    total = row.total_requests or 0
    error_count = row.error_count or 0
    return {
        "total_conversations": conv_count,
        "total_messages": msg_count,
        "total_requests": total,
        "total_tokens": int(row.total_tokens or 0),
        "avg_latency_ms": round(float(row.avg_latency_ms), 1) if row.avg_latency_ms else None,
        "error_rate": round(error_count / total, 4) if total else 0.0,
    }


async def get_latency(
    db: AsyncSession,
    from_dt: datetime,
    to_dt: datetime,
    bucket: str,
    provider: str | None = None,
    model: str | None = None,
) -> dict:
    if bucket not in _VALID_BUCKETS:
        bucket = "hour"

    filters = "WHERE status = 'success' AND request_at BETWEEN :from_dt AND :to_dt"
    params: dict = {"from_dt": from_dt, "to_dt": to_dt}
    if provider:
        filters += " AND provider = :provider"
        params["provider"] = provider
    if model:
        filters += " AND model = :model"
        params["model"] = model

    overall = (
        await db.execute(
            text(f"""
                SELECT
                    PERCENTILE_CONT(0.50) WITHIN GROUP (ORDER BY latency_ms) AS p50,
                    PERCENTILE_CONT(0.90) WITHIN GROUP (ORDER BY latency_ms) AS p90,
                    PERCENTILE_CONT(0.99) WITHIN GROUP (ORDER BY latency_ms) AS p99,
                    AVG(latency_ms)                                           AS avg_ms,
                    COUNT(*)                                                  AS total
                FROM inference_logs
                {filters}
            """),
            params,
        )
    ).one()

    buckets_rows = (
        await db.execute(
            text(f"""
                SELECT
                    DATE_TRUNC('{bucket}', request_at)                         AS ts,
                    PERCENTILE_CONT(0.50) WITHIN GROUP (ORDER BY latency_ms)   AS p50,
                    PERCENTILE_CONT(0.90) WITHIN GROUP (ORDER BY latency_ms)   AS p90,
                    PERCENTILE_CONT(0.99) WITHIN GROUP (ORDER BY latency_ms)   AS p99,
                    AVG(latency_ms)                                             AS avg_ms,
                    COUNT(*)                                                    AS count
                FROM inference_logs
                {filters}
                GROUP BY 1
                ORDER BY 1
            """),
            params,
        )
    ).all()

    def _ms(v) -> float | None:
        return round(float(v), 1) if v is not None else None

    return {
        "p50": _ms(overall.p50),
        "p90": _ms(overall.p90),
        "p99": _ms(overall.p99),
        "avg": _ms(overall.avg_ms),
        "total": overall.total,
        "buckets": [
            {
                "timestamp": row.ts.isoformat(),
                "p50": _ms(row.p50),
                "p90": _ms(row.p90),
                "p99": _ms(row.p99),
                "avg": _ms(row.avg_ms),
                "count": row.count,
            }
            for row in buckets_rows
        ],
    }


async def get_throughput(
    db: AsyncSession,
    from_dt: datetime,
    to_dt: datetime,
    bucket: str,
) -> dict:
    if bucket not in _VALID_BUCKETS:
        bucket = "hour"

    params: dict = {"from_dt": from_dt, "to_dt": to_dt}

    overall = (
        await db.execute(
            text("""
                SELECT
                    COUNT(*)                    AS total_requests,
                    COALESCE(SUM(total_tokens), 0) AS total_tokens
                FROM inference_logs
                WHERE request_at BETWEEN :from_dt AND :to_dt
            """),
            params,
        )
    ).one()

    bucket_rows = (
        await db.execute(
            text(f"""
                SELECT
                    DATE_TRUNC('{bucket}', request_at)     AS ts,
                    COUNT(*)                               AS count,
                    COALESCE(SUM(total_tokens), 0)         AS tokens,
                    COALESCE(SUM(prompt_tokens), 0)        AS prompt_tokens,
                    COALESCE(SUM(completion_tokens), 0)    AS completion_tokens
                FROM inference_logs
                WHERE request_at BETWEEN :from_dt AND :to_dt
                GROUP BY 1
                ORDER BY 1
            """),
            params,
        )
    ).all()

    return {
        "total_requests": overall.total_requests,
        "total_tokens": int(overall.total_tokens),
        "buckets": [
            {
                "timestamp": row.ts.isoformat(),
                "count": row.count,
                "tokens": int(row.tokens),
                "prompt_tokens": int(row.prompt_tokens),
                "completion_tokens": int(row.completion_tokens),
            }
            for row in bucket_rows
        ],
    }


async def get_errors(
    db: AsyncSession,
    from_dt: datetime,
    to_dt: datetime,
) -> dict:
    params: dict = {"from_dt": from_dt, "to_dt": to_dt}

    overall = (
        await db.execute(
            text("""
                SELECT
                    COUNT(*)                                   AS total,
                    COUNT(*) FILTER (WHERE status = 'error')  AS error_count
                FROM inference_logs
                WHERE request_at BETWEEN :from_dt AND :to_dt
            """),
            params,
        )
    ).one()

    by_provider = (
        await db.execute(
            text("""
                SELECT
                    provider,
                    COUNT(*)                                   AS total,
                    COUNT(*) FILTER (WHERE status = 'error')  AS error_count
                FROM inference_logs
                WHERE request_at BETWEEN :from_dt AND :to_dt
                GROUP BY provider
                ORDER BY error_count DESC
            """),
            params,
        )
    ).all()

    by_type = (
        await db.execute(
            text("""
                SELECT
                    SPLIT_PART(COALESCE(error_message, 'unknown'), ' ', 1) AS error_type,
                    COUNT(*) AS count
                FROM inference_logs
                WHERE status = 'error'
                  AND request_at BETWEEN :from_dt AND :to_dt
                GROUP BY 1
                ORDER BY count DESC
                LIMIT 10
            """),
            params,
        )
    ).all()

    total = overall.total or 0
    error_count = overall.error_count or 0
    return {
        "total": total,
        "error_count": error_count,
        "error_rate": round(error_count / total, 4) if total else 0.0,
        "by_provider": [
            {
                "provider": row.provider,
                "total": row.total,
                "error_count": row.error_count,
                "error_rate": round(row.error_count / row.total, 4) if row.total else 0.0,
            }
            for row in by_provider
        ],
        "by_type": [
            {"error_type": row.error_type, "count": row.count}
            for row in by_type
        ],
    }
