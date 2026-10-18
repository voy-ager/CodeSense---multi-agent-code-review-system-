# api/server.py

import sys
import os
import json
import logging
from contextlib import asynccontextmanager

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from agent.graph import build_graph
from database.connection import get_pool, close_pool
from database.crud import save_review, get_recent_reviews, get_stats
from cache.redis_client import get_cached_review, cache_review

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ── Lifespan: startup + shutdown ──────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    FastAPI lifespan replaces the old @app.on_event("startup") pattern.
    Everything before `yield` runs at startup.
    Everything after `yield` runs at shutdown.

    We initialize the DB pool here so it's ready before the first request.
    The LangGraph pipeline is also compiled once here — not per-request.
    """
    logger.info("Starting CodeSense API...")

    # Initialize PostgreSQL pool (gracefully fails if DB is not running)
    await get_pool()

    # Compile the LangGraph pipeline once at startup
    app.state.graph = build_graph()
    logger.info("LangGraph pipeline compiled. Server ready.")

    yield  # Server is running

    # Shutdown: close DB connections cleanly
    await close_pool()
    logger.info("CodeSense API shut down.")


# ── App setup ─────────────────────────────────────────────────────────────────
app = FastAPI(
    title="CodeSense API",
    description="Multi-agent AI code review — security, performance, testing, style.",
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Request models ────────────────────────────────────────────────────────────
class ReviewRequest(BaseModel):
    pr_url: str


# ── Helper ────────────────────────────────────────────────────────────────────
def build_initial_state(pr_url: str) -> dict:
    return {
        "pr_url":            pr_url.strip(),
        "raw_diff":          "",
        "pr_metadata":       {},
        "security_findings": [],
        "perf_findings":     [],
        "test_findings":     [],
        "style_findings":    [],
        "final_report":      {},
        "failed_agents":     [],
        "error":             "",
    }


async def persist(pr_url: str, report: dict) -> str | None:
    """Cache + save a report. Incomplete reports are skipped so a transient
    LLM failure isn't served from cache for the next hour."""
    if report.get("failed_agents"):
        return None
    await cache_review(pr_url, report)
    return await save_review(report)


def validate_pr_url(pr_url: str) -> None:
    if not pr_url.startswith("https://github.com/"):
        raise HTTPException(
            status_code=400,
            detail="URL must be a valid GitHub PR URL starting with https://github.com/"
        )
    if "/pull/" not in pr_url:
        raise HTTPException(
            status_code=400,
            detail="URL must point to a pull request — must contain /pull/"
        )


# ── Routes ────────────────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    """Health check — confirms server, graph, DB, and cache status."""
    pool  = await get_pool()
    db_ok = pool is not None

    try:
        from cache.redis_client import get_client
        await get_client().ping()
        redis_ok = True
    except Exception:
        redis_ok = False

    return {
        "status":   "ok",
        "agents":   ["security", "performance", "testing", "style"],
        "database": "connected" if db_ok    else "unavailable",
        "cache":    "connected" if redis_ok else "unavailable",
    }


@app.post("/review")
async def review(request: ReviewRequest):
    """
    Analyze a GitHub PR. Checks Redis cache first — returns in <1s on a hit.
    On a cache miss, runs the full 4-agent pipeline, then saves to both
    PostgreSQL (permanent) and Redis (1-hour TTL).
    """
    validate_pr_url(request.pr_url)

    # ── Cache check ───────────────────────────────────────────────────────
    cached = await get_cached_review(request.pr_url)
    if cached:
        return {
            "report":   cached,
            "cached":   True,
            "metadata": {
                "pr_url":            request.pr_url,
                "total_findings":    cached.get("total_findings", 0),
                "cache":             "HIT — returned in <1s",
            }
        }

    # ── Cache miss: run the full pipeline ─────────────────────────────────
    try:
        initial_state = build_initial_state(request.pr_url)
        # ainvoke runs the sync nodes in a thread pool, so a 30s review
        # doesn't freeze every other request on the event loop.
        result        = await app.state.graph.ainvoke(initial_state)

        if result.get("error"):
            raise HTTPException(status_code=422, detail=result["error"])

        report    = result.get("final_report", {})
        review_id = await persist(request.pr_url, report)

        return {
            "report":   report,
            "cached":   False,
            "metadata": {
                "pr_url":         request.pr_url,
                "review_id":      review_id,
                "total_findings": report.get("total_findings", 0),
                "agents_ran":     ["security", "performance", "testing", "style"],
                "cache":          "MISS — full pipeline ran",
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# node name → (SSE status the frontend listens for, display label, findings key)
AGENT_EVENTS = {
    "security_agent": ("security_done", "Security",    "security_findings"),
    "perf_agent":     ("perf_done",     "Performance", "perf_findings"),
    "test_agent":     ("test_done",     "Testing",     "test_findings"),
    "style_agent":    ("style_done",    "Style",       "style_findings"),
}


@app.post("/review/stream")
async def review_stream(request: ReviewRequest):
    """
    Streaming version of /review. Returns SSE events as each agent completes.
    On a cache hit, streams the cached result immediately.
    On a cache miss, runs the pipeline and streams progress in real time.
    """
    validate_pr_url(request.pr_url)

    # ── Cache hit: stream the cached result immediately ───────────────────
    cached = await get_cached_review(request.pr_url)
    if cached:
        async def stream_cache():
            yield f"data: {json.dumps({'status': 'cache_hit', 'message': 'Returning cached review'})}\n\n"
            yield f"data: {json.dumps({'status': 'complete', 'report': cached, 'cached': True})}\n\n"
            yield "data: [DONE]\n\n"
        return StreamingResponse(stream_cache(), media_type="text/event-stream")

    # ── Cache miss: run pipeline and stream progress ──────────────────────
    async def event_stream():
        try:
            yield f"data: {json.dumps({'status': 'starting', 'message': 'Fetching PR diff from GitHub...'})}\n\n"

            initial_state = build_initial_state(request.pr_url)
            final_report  = {}

            async for event in app.state.graph.astream(initial_state):
                node_name = list(event.keys())[0]
                node_data = event[node_name]

                if node_name == "ingest_diff":
                    if node_data.get("error"):
                        yield f"data: {json.dumps({'status': 'error', 'message': node_data['error']})}\n\n"
                        yield "data: [DONE]\n\n"
                        return
                    meta  = node_data.get("pr_metadata", {})
                    title = meta.get("title", "")
                    files = meta.get("files_changed", 0)
                    msg   = f"PR: '{title}' — {files} files changed"
                    yield f"data: {json.dumps({'status': 'diff_fetched', 'message': msg})}\n\n"

                elif node_name in AGENT_EVENTS:
                    status, label, key = AGENT_EVENTS[node_name]
                    if node_data.get("failed_agents"):
                        status, msg = "agent_failed", f"{label}: agent failed — results incomplete"
                    else:
                        msg = f"{label}: {len(node_data.get(key, []))} issue(s) found"
                    yield f"data: {json.dumps({'status': status, 'message': msg})}\n\n"

                elif node_name == "synthesize":
                    if node_data.get("error"):
                        yield f"data: {json.dumps({'status': 'error', 'message': node_data['error']})}\n\n"
                        break
                    final_report = node_data.get("final_report", {})
                    yield f"data: {json.dumps({'status': 'complete', 'report': final_report, 'cached': False})}\n\n"

            # Save to cache and DB after streaming completes
            if final_report:
                await persist(request.pr_url, final_report)

            yield "data: [DONE]\n\n"

        except Exception as e:
            yield f"data: {json.dumps({'status': 'error', 'message': str(e)})}\n\n"
            yield "data: [DONE]\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@app.get("/reviews/recent")
async def recent_reviews(limit: int = 10):
    """Return the most recent reviews from PostgreSQL for the dashboard."""
    reviews = await get_recent_reviews(limit=min(limit, 50))
    return {"reviews": reviews, "count": len(reviews)}


@app.get("/reviews/stats")
async def review_stats():
    """Aggregate stats across all reviews — for the dashboard summary cards."""
    stats = await get_stats()
    return stats


@app.get("/sources")
def list_sources():
    return {"message": "Sources endpoint available. Submit a PR URL to /review."}