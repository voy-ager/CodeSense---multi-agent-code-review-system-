# cache/redis_client.py

import redis.asyncio as redis
import json
import hashlib
import os
import logging

logger = logging.getLogger(__name__)

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")

# How long to cache a review result.
# 1 hour is a reasonable TTL — PRs can receive new commits,
# so we don't want to serve stale results indefinitely.
CACHE_TTL_SECONDS = 3600

# Single shared async Redis client.
# redis.asyncio handles connection pooling internally.
_client: redis.Redis | None = None


def get_client() -> redis.Redis:
    global _client
    if _client is None:
        _client = redis.from_url(REDIS_URL, decode_responses=True)
    return _client


def _cache_key(pr_url: str) -> str:
    """
    Convert a PR URL into a Redis key.

    We hash the URL rather than using it directly because:
    1. URLs can contain characters that are awkward in Redis keys
    2. Keys stay a consistent, short length regardless of URL length
    """
    url_hash = hashlib.sha256(pr_url.lower().strip().encode()).hexdigest()[:20]
    return f"codesense:review:{url_hash}"


async def get_cached_review(pr_url: str) -> dict | None:
    """
    Look up a cached review for this PR URL.
    Returns the full report dict if found, None if not cached or Redis is down.
    """
    try:
        client = get_client()
        cached = await client.get(_cache_key(pr_url))
        if cached:
            logger.info(f"Cache HIT for {pr_url}")
            return json.loads(cached)
        logger.info(f"Cache MISS for {pr_url}")
        return None
    except Exception as e:
        # Redis being down should never crash the API
        logger.warning(f"Redis unavailable, skipping cache read: {e}")
        return None


async def cache_review(pr_url: str, report: dict) -> None:
    """
    Store a review report in Redis with a TTL.
    Silently fails if Redis is unavailable.
    """
    try:
        client  = get_client()
        key     = _cache_key(pr_url)
        payload = json.dumps(report)
        await client.setex(key, CACHE_TTL_SECONDS, payload)
        logger.info(f"Cached review for {pr_url} (TTL: {CACHE_TTL_SECONDS}s)")
    except Exception as e:
        logger.warning(f"Redis unavailable, skipping cache write: {e}")


async def invalidate_review(pr_url: str) -> None:
    """Delete a cached review — useful if a PR gets new commits."""
    try:
        client = get_client()
        await client.delete(_cache_key(pr_url))
        logger.info(f"Cache invalidated for {pr_url}")
    except Exception as e:
        logger.warning(f"Redis unavailable, skipping invalidation: {e}")