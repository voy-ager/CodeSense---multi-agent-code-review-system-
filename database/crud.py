# database/crud.py

import json
import logging
from database.connection import get_pool

logger = logging.getLogger(__name__)


async def save_review(report: dict) -> str | None:
    """
    Persist a completed review report to PostgreSQL.

    Returns the UUID of the saved row, or None if the DB is unavailable.
    Failing to save never crashes the API — the user still gets their review.
    """
    pool = await get_pool()
    if pool is None:
        return None

    by_severity = report.get("by_severity", {})
    by_agent    = report.get("by_agent",    {})

    try:
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO reviews (
                    pr_url,    pr_title,  author,
                    total_findings,
                    critical_count, high_count, medium_count, low_count,
                    security_count, performance_count, testing_count, style_count,
                    findings, summary
                )
                VALUES (
                    $1,  $2,  $3,
                    $4,
                    $5,  $6,  $7,  $8,
                    $9,  $10, $11, $12,
                    $13::jsonb, $14
                )
                RETURNING id
                """,
                report.get("pr_url",   ""),
                report.get("pr_title", ""),
                report.get("author",   ""),
                report.get("total_findings", 0),
                by_severity.get("critical",    0),
                by_severity.get("high",        0),
                by_severity.get("medium",      0),
                by_severity.get("low",         0),
                by_agent.get("security",       0),
                by_agent.get("performance",    0),
                by_agent.get("testing",        0),
                by_agent.get("style",          0),
                json.dumps(report.get("findings", [])),
                report.get("summary", ""),
            )
            review_id = str(row["id"])
            logger.info(f"Review saved to PostgreSQL: {review_id}")
            return review_id

    except Exception as e:
        logger.error(f"Failed to save review: {e}")
        return None


async def get_recent_reviews(limit: int = 10) -> list[dict]:
    """
    Fetch the most recent reviews for the dashboard.
    Returns only summary columns — not the full findings JSONB —
    to keep the query fast.
    """
    pool = await get_pool()
    if pool is None:
        return []

    try:
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT
                    id, pr_url, pr_title, author,
                    total_findings, critical_count, high_count,
                    medium_count, low_count, created_at
                FROM reviews
                ORDER BY created_at DESC
                LIMIT $1
                """,
                limit,
            )
            return [
                {
                    **dict(row),
                    "id":         str(row["id"]),
                    "created_at": row["created_at"].isoformat(),
                }
                for row in rows
            ]

    except Exception as e:
        logger.error(f"Failed to fetch recent reviews: {e}")
        return []


async def get_stats() -> dict:
    """
    Aggregate stats across all reviews for a dashboard summary.
    Single query using SUM/COUNT — fast even with thousands of rows.
    """
    pool = await get_pool()
    if pool is None:
        return {}

    try:
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT
                    COUNT(*)                    AS total_reviews,
                    COALESCE(SUM(total_findings),  0) AS total_findings,
                    COALESCE(SUM(critical_count),  0) AS total_critical,
                    COALESCE(SUM(security_count),  0) AS total_security,
                    COALESCE(SUM(testing_count),   0) AS total_testing
                FROM reviews
                """
            )
            return dict(row)

    except Exception as e:
        logger.error(f"Failed to fetch stats: {e}")
        return {}