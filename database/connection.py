# database/connection.py

import asyncpg
import os
import logging

logger = logging.getLogger(__name__)

# Default URL works when running locally without Docker.
# When running inside docker-compose, DATABASE_URL is set
# to use the 'postgres' service name as the host.
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://codesense:codesense_dev@localhost:5432/codesense"
)

# Module-level pool — created once at startup, reused on every request.
# asyncpg pools handle concurrent requests without blocking — each
# request checks out a connection, uses it, and returns it to the pool.
_pool: asyncpg.Pool | None = None


async def get_pool() -> asyncpg.Pool:
    """
    Return the shared connection pool, creating it on first call.
    min_size=2: keep 2 connections warm at all times (fast response)
    max_size=10: never exceed 10 concurrent DB connections
    """
    global _pool
    if _pool is None:
        try:
            _pool = await asyncpg.create_pool(
                DATABASE_URL,
                min_size=2,
                max_size=10,
                command_timeout=30,
            )
            logger.info("PostgreSQL connection pool created")
        except Exception as e:
            logger.warning(f"PostgreSQL not available: {e}. Reviews will not be persisted.")
            return None
    return _pool


async def close_pool() -> None:
    """Close the pool cleanly on application shutdown."""
    global _pool
    if _pool:
        await _pool.close()
        _pool = None
        logger.info("PostgreSQL connection pool closed")