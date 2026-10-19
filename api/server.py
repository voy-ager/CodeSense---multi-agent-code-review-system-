# api/server.py

import asyncio
import sys
import os
import json
import logging
import secrets
from contextlib import asynccontextmanager

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from agent.graph import build_graph, initial_state
from database.connection import get_pool, close_pool
from database.crud import save_review, get_recent_reviews, get_stats
from cache.redis_client import get_cached_review, cache_review, REDIS_URL
from tools.github import canonical_pr_url, fetch_head_sha

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
DOCS_PATHS = {"/docs", "/docs/oauth2-redirect", "/redoc", "/openapi.json"}
# Interactive docs reveal every endpoint; set EXPOSE_DOCS=false in production.
EXPOSE_DOCS = os.getenv("EXPOSE_DOCS", "true").lower() == "true"

# Rate limits live in Redis so they hold across workers; if Redis is down,
# each worker falls back to its own in-memory counter rather than failing open.
# headers_enabled adds X-RateLimit-* and Retry-After so clients know when to retry.
limiter = Limiter(key_func=get_remote_address, storage_uri=REDIS_URL,
                  in_memory_fallback_enabled=True, headers_enabled=True)


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
    docs_url="/docs" if EXPOSE_DOCS else None,
    redoc_url="/redoc" if EXPOSE_DOCS else None,
    openapi_url="/openapi.json" if EXPOSE_DOCS else None,
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
    # Exact match: a prefix check would also exempt /docsX, /docs-anything, ...
    if request.url.path not in DOCS_PATHS:
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


@app.exception_handler(RequestValidationError)
async def validation_error(request: Request, exc: RequestValidationError):
    # FastAPI's default echoes the submitted input back; return only what was wrong.
    errors = [{"loc": list(e.get("loc", [])), "msg": e.get("msg", "")} for e in exc.errors()]
    return JSONResponse({"detail": errors}, status_code=422)


# ── Helpers ───────────────────────────────────────────────────────────────────
async def persist(pr_url: str, report: dict) -> str | None:
    """Cache + save a report. Incomplete reports are skipped so a transient
    LLM failure isn't served from cache for the next hour."""
    if report.get("failed_agents"):
        return None
    if report.get("head_sha"):
        await cache_review(f"{pr_url}@{report['head_sha']}", report)
        await cache_review(f"{pr_url}@latest", report)
    return await save_review(report)


async def cached_review(pr_url: str) -> dict | None:
    """The cache is keyed by the PR's head commit, so pushing new commits always
    triggers a fresh review instead of serving the old one for up to an hour.
    If GitHub can't tell us the head commit (rate limit, outage), serve the most
    recent review of this PR, flagged as possibly stale, rather than nothing."""
    head_sha = await asyncio.to_thread(fetch_head_sha, pr_url)
    if head_sha:
        return await get_cached_review(f"{pr_url}@{head_sha}")
    latest = await get_cached_review(f"{pr_url}@latest")
    return {**latest, "stale": True} if latest else None


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


# ── Review jobs ───────────────────────────────────────────────────────────────
# Groq's free tier gives all reviews one shared token budget, so reviews run one at a
# time (MAX_CONCURRENT_REVIEWS) and queue instead of failing each other with 429s.
PIPELINE_SLOTS = asyncio.Semaphore(int(os.getenv("MAX_CONCURRENT_REVIEWS", "1")))


class ReviewJob:
    """One pipeline run per PR, shared by every request for that PR (single-flight).
    It runs detached from the request, so a client that disconnects mid-review
    doesn't waste the LLM budget: the result is still cached for the next request."""

    def __init__(self):
        self.events: list[tuple[str, dict]] = []
        self.final_report: dict = {}
        self.error = ""
        self.crashed = False
        self.done = False
        self.cond = asyncio.Condition()

    async def publish(self, node: str, data: dict) -> None:
        async with self.cond:
            self.events.append((node, data))
            self.cond.notify_all()

    async def finish(self) -> None:
        async with self.cond:
            self.done = True
            self.cond.notify_all()

    async def follow(self):
        """Replay every event so far, then stream new ones until the job ends."""
        i = 0
        while True:
            async with self.cond:
                await self.cond.wait_for(lambda: i < len(self.events) or self.done)
                batch, finished = self.events[i:], self.done
            i += len(batch)
            for event in batch:
                yield event
            if finished and i >= len(self.events):
                return


JOBS: dict[str, ReviewJob] = {}
_RUNNING: set[asyncio.Task] = set()   # strong refs so running jobs aren't garbage-collected


async def _run_job(pr_url: str, job: ReviewJob) -> None:
    try:
        async with PIPELINE_SLOTS:
            async for event in app.state.graph.astream(initial_state(pr_url)):
                node, data = next(iter(event.items()))
                if data.get("error"):
                    job.error = data["error"]
                if node == "synthesize":
                    job.final_report = data.get("final_report", {})
                await job.publish(node, data)
        if job.final_report:
            await persist(pr_url, job.final_report)
    except Exception:
        # Log the details server-side; never leak internals to the client.
        logger.exception("Review failed for %s", pr_url)
        job.crashed, job.error = True, "Review failed — please try again"
    finally:
        JOBS.pop(pr_url, None)
        await job.finish()


def review_job(pr_url: str) -> ReviewJob:
    job = JOBS.get(pr_url)
    if job is None:
        job = JOBS[pr_url] = ReviewJob()
        task = asyncio.create_task(_run_job(pr_url, job))
        _RUNNING.add(task)
        task.add_done_callback(_RUNNING.discard)
    return job


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


# /review and /review/stream share one budget, so alternating endpoints doesn't double it.
review_limit = limiter.shared_limit("10/minute", scope="review")


@app.post("/review")
@review_limit
async def review(request: Request, response: Response, body: ReviewRequest):
    """
    Analyze a GitHub PR. Checks Redis cache first — returns in <1s on a hit.
    On a cache miss, runs (or joins) the pipeline, then saves to both
    PostgreSQL (permanent) and Redis (1-hour TTL).
    """
    pr_url = validate_pr_url(body.pr_url)

    cached = await cached_review(pr_url)
    if cached:
        return {
            "report":   cached,
            "cached":   True,
            "metadata": {
                "pr_url":         pr_url,
                "total_findings": cached.get("total_findings", 0),
                "cache":          "HIT (possibly stale: GitHub unreachable)" if cached.get("stale") else "HIT",
            }
        }

    job = review_job(pr_url)
    async for _ in job.follow():
        pass
    if job.crashed:
        raise HTTPException(status_code=500, detail=job.error)
    if job.error and not job.final_report:
        raise HTTPException(status_code=422, detail=job.error)

    report = job.final_report
    return {
        "report":   report,
        "cached":   False,
        "metadata": {
            "pr_url":         pr_url,
            "total_findings": report.get("total_findings", 0),
            "agents_ran":     ["security", "performance", "testing", "style"],
            "cache":          "MISS — full pipeline ran",
        }
    }


# node name → (SSE status the frontend listens for, display label, findings key)
AGENT_EVENTS = {
    "security_agent": ("security_done", "Security",    "security_findings"),
    "perf_agent":     ("perf_done",     "Performance", "perf_findings"),
    "test_agent":     ("test_done",     "Testing",     "test_findings"),
    "style_agent":    ("style_done",    "Style",       "style_findings"),
    "static_scan":    ("static_done",   "Static checks (secrets, deps, injection)", "static_findings"),
}


def sse(payload: dict) -> str:
    return f"data: {json.dumps(payload)}\n\n"


@app.post("/review/stream")
@review_limit
async def review_stream(request: Request, body: ReviewRequest):
    """
    Streaming version of /review. Returns SSE events as each agent completes.
    On a cache hit, streams the cached result immediately. Concurrent requests
    for the same PR share one pipeline run.
    """
    pr_url = validate_pr_url(body.pr_url)

    cached = await cached_review(pr_url)
    if cached:
        async def stream_cache():
            note = " (possibly stale: GitHub unreachable)" if cached.get("stale") else ""
            yield sse({"status": "cache_hit", "message": "Returning cached review" + note})
            yield sse({"status": "complete", "report": cached, "cached": True})
            yield "data: [DONE]\n\n"
        return StreamingResponse(stream_cache(), media_type="text/event-stream")

    job = review_job(pr_url)

    async def event_stream():
        yield sse({"status": "starting", "message": "Fetching PR diff from GitHub..."})
        async for node, data in job.follow():
            if data.get("error"):
                yield sse({"status": "error", "message": data["error"]})
            elif node == "ingest_diff":
                meta = data.get("pr_metadata", {})
                yield sse({"status": "diff_fetched",
                           "message": f"PR: '{meta.get('title', '')}' — {meta.get('files_changed', 0)} files changed"})
            elif node in AGENT_EVENTS:
                status, label, key = AGENT_EVENTS[node]
                if data.get("failed_agents"):
                    status, msg = "agent_failed", f"{label}: agent failed — results incomplete"
                else:
                    msg = f"{label}: {len(data.get(key, []))} issue(s) found"
                yield sse({"status": status, "message": msg})
            elif node == "synthesize":
                yield sse({"status": "complete", "report": data.get("final_report", {}), "cached": False})
        if job.crashed:
            yield sse({"status": "error", "message": job.error})
        yield "data: [DONE]\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@app.get("/reviews/recent", dependencies=[Depends(require_api_key)])
@limiter.limit("30/minute")
async def recent_reviews(request: Request, response: Response, limit: int = Query(10, ge=1, le=50)):
    """Return the most recent reviews from PostgreSQL for the dashboard."""
    reviews = await get_recent_reviews(limit=limit)
    return {"reviews": reviews, "count": len(reviews)}


@app.get("/reviews/stats", dependencies=[Depends(require_api_key)])
@limiter.limit("30/minute")
async def review_stats(request: Request, response: Response):
    """Aggregate stats across all reviews — for the dashboard summary cards."""
    stats = await get_stats()
    return stats
