-- PostgreSQL schema for CodeSense
-- This file runs automatically when Docker starts the database for the first time

CREATE EXTENSION IF NOT EXISTS "pgcrypto";

CREATE TABLE IF NOT EXISTS reviews (
    -- Primary key using UUID for distribution-safe IDs
    id              UUID        PRIMARY KEY DEFAULT gen_random_uuid(),

    -- PR metadata fetched from GitHub
    pr_url          TEXT        NOT NULL,
    pr_title        TEXT,
    author          TEXT,

    -- Aggregate counts for quick dashboard queries
    -- Storing these as separate columns avoids parsing the full JSONB on every list query
    total_findings  INTEGER     DEFAULT 0,
    critical_count  INTEGER     DEFAULT 0,
    high_count      INTEGER     DEFAULT 0,
    medium_count    INTEGER     DEFAULT 0,
    low_count       INTEGER     DEFAULT 0,

    -- Per-agent counts for the agent breakdown panel
    security_count    INTEGER   DEFAULT 0,
    performance_count INTEGER   DEFAULT 0,
    testing_count     INTEGER   DEFAULT 0,
    style_count       INTEGER   DEFAULT 0,

    -- Full findings array stored as JSONB for flexible querying
    -- JSONB is indexed and queryable unlike TEXT JSON
    findings        JSONB       NOT NULL DEFAULT '[]',
    summary         TEXT,

    -- Timezone-aware timestamp for correct ordering across regions
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- Index for looking up reviews by PR URL (cache miss fallback)
CREATE INDEX IF NOT EXISTS idx_reviews_pr_url
    ON reviews(pr_url);

-- Index for the recent reviews feed (most common query)
CREATE INDEX IF NOT EXISTS idx_reviews_created_at
    ON reviews(created_at DESC);

-- Index for severity filtering on the dashboard
CREATE INDEX IF NOT EXISTS idx_reviews_critical
    ON reviews(critical_count DESC)
    WHERE critical_count > 0;