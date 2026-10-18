# api/server.py

import sys
import os
import json
import logging
import secrets
from contextlib import asynccontextmanager

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from agent.graph import build_graph
from database.connection import get_pool, close_pool
from database.crud import save_review, get_recent_reviews, get_stats
from cache.redis_client import get_cached_review, cache_review, REDIS_URL
from tools.github import canonical_pr_url

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Comma-separated list of frontend origins allowed to call the API from a browser.
ALLOWED_ORIGINS = [o.strip() for o in os.getenv("ALLOWED_ORIGINS", "http://localhost:3000").split(",") if o.strip()]

# The largest legitimate body is {"pr_url": "..."} — 1MB is a generous ceiling.
MAX_BODY_BYTES = 1_000_000

SECURITY_HEADERS = {
    "X-Content-Type-Options":    "nosniff",
    "X-Frame-Options":           "DENY",
    "Referrer-Policy":           "no-referrer",
    "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
    "Permissions-Policy":        "camera=(), microphone=(), geolocation=()",
}
# The API only returns JSON/SSE, so nothing may load — except Swagger UI, which pulls CDN assets.
API_CSP = "default-src 'none'; frame-ancestors 'none'"
DOCS_PATHS = ("/docs", "/redoc", "/openapi.json")

# Rate limits live in Redis so they hold across workers; if Redis is down,
# each worker falls back to its own in-memory counter rather than failing open.
limiter = Limiter(key_func=get_remote_address, storage_uri=REDIS_URL, in_memory_fallback_enabled=True)


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

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


@app.middleware("http")
async def harden(request: Request, call_next):
    """Reject oversized bodies before they're read, and add security headers."""
    if request.method in ("POST", "PUT", "PATCH"):
        length = request.headers.get("content-length")
        # Chunked bodies have no length to check up front, so they're refused outright.
        if length is None:
            return JSONResponse({"detail": "Content-Length header required"}, status_code=411)
        if not length.isdigit() or int(length) > MAX_BODY_BYTES:
            return JSONResponse({"detail": "Request body too large"}, status_code=413)

    response = await call_next(request)
    response.headers.update(SECURITY_HEADERS)
    if not request.url.path.startswith(DOCS_PATHS):
        response.headers["Content-Security-Policy"] = API_CSP
    return response


# Added after harden so CORS is the outermost layer — 411/413 responses still carry CORS headers.
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "X-API-Key"],
)


# ── Request models ────────────────────────────────────────────────────────────
class ReviewRequest(BaseModel):
    pr_url: str = Field(max_length=500)


# ── Helper ────────────────────────────────────────────────────────────────────
def build_initial_state(pr_url: str) -> dict:
    return {
        "pr_url":            pr_url,
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


def validate_pr_url(pr_url: str) -> str:
    """Return the canonical PR URL, or reject anything that isn't a GitHub PR link."""
    canonical = canonical_pr_url(pr_url)
    if not canonical:
        raise HTTPException(
            status_code=400,
            detail="URL must be a GitHub pull request, e.g. https://github.com/owner/repo/pull/123"
        )
    return canonical


def require_api_key(x_api_key: str = Header(default="")) -> None:
    """Admin endpoints expose every review ever run, so they need ADMIN_API_KEY.
    If the key isn't configured the endpoints stay locked (fail closed)."""
    expected = os.getenv("ADMIN_API_KEY", "")
    if not expected or not secrets.compare_digest(x_api_key.encode(), expected.encode()):
        raise HTTPException(status_code=401, detail="Invalid or missing API key")


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
@limiter.limit("10/minute")
async def review(request: Request, body: ReviewRequest):
    """
    Analyze a GitHub PR. Checks Redis cache first — returns in <1s on a hit.
    On a cache miss, runs the full 4-agent pipeline, then saves to both
    PostgreSQL (permanent) and Redis (1-hour TTL).
    """
    pr_url = validate_pr_url(body.pr_url)

    # ── Cache check ───────────────────────────────────────────────────────
    cached = await get_cached_review(pr_url)
    if cached:
        return {
            "report":   cached,
            "cached":   True,
            "metadata": {
                "pr_url":            pr_url,
                "total_findings":    cached.get("total_findings", 0),
                "cache":             "HIT — returned in <1s",
            }
        }

    # ── Cache miss: run the full pipeline ─────────────────────────────────
    try:
        initial_state = build_initial_state(pr_url)
        # ainvoke runs the sync nodes in a thread pool, so a 30s review
        # doesn't freeze every other request on the event loop.
        result        = await app.state.graph.ainvoke(initial_state)

        if result.get("error"):
            raise HTTPException(status_code=422, detail=result["error"])

        report    = result.get("final_report", {})
        review_id = await persist(pr_url, report)

        return {
            "report":   report,
            "cached":   False,
            "metadata": {
                "pr_url":         pr_url,
                "review_id":      review_id,
                "total_findings": report.get("total_findings", 0),
                "agents_ran":     ["security", "performance", "testing", "style"],
                "cache":          "MISS — full pipeline ran",
            }
        }

    except HTTPException:
        raise
    except Exception:
        # Log the details server-side; don't leak internals to the client.
        logger.exception("Review failed for %s", pr_url)
        raise HTTPException(status_code=500, detail="Review failed — please try again")


# node name → (SSE status the frontend listens for, display label, findings key)
AGENT_EVENTS = {
    "security_agent": ("security_done", "Security",    "security_findings"),
    "perf_agent":     ("perf_done",     "Performance", "perf_findings"),
    "test_agent":     ("test_done",     "Testing",     "test_findings"),
    "style_agent":    ("style_done",    "Style",       "style_findings"),
}


@app.post("/review/stream")
@limiter.limit("10/minute")
async def review_stream(request: Request, body: ReviewRequest):
    """
    Streaming version of /review. Returns SSE events as each agent completes.
    On a cache hit, streams the cached result immediately.
    On a cache miss, runs the pipeline and streams progress in real time.
    """
    pr_url = validate_pr_url(body.pr_url)

    # ── Cache hit: stream the cached result immediately ───────────────────
    cached = await get_cached_review(pr_url)
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

            initial_state = build_initial_state(pr_url)
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
                await persist(pr_url, final_report)

            yield "data: [DONE]\n\n"

        except Exception:
            logger.exception("Streaming review failed for %s", pr_url)
            yield f"data: {json.dumps({'status': 'error', 'message': 'Review failed — please try again'})}\n\n"
            yield "data: [DONE]\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@app.get("/reviews/recent", dependencies=[Depends(require_api_key)])
@limiter.limit("30/minute")
async def recent_reviews(request: Request, limit: int = Query(10, ge=1, le=50)):
    """Return the most recent reviews from PostgreSQL for the dashboard."""
    reviews = await get_recent_reviews(limit=limit)
    return {"reviews": reviews, "count": len(reviews)}


@app.get("/reviews/stats", dependencies=[Depends(require_api_key)])
@limiter.limit("30/minute")
async def review_stats(request: Request):
    """Aggregate stats across all reviews — for the dashboard summary cards."""
    stats = await get_stats()
    return stats
