# CodeSense

Multi-agent AI code review. Paste a GitHub pull request URL; four specialist agents review
**security**, **performance**, **test coverage**, and **style** in parallel and return one
severity-ranked report with a concrete fix for every finding.

```
              ┌─ security_agent ──┐
ingest_diff ──┼─ perf_agent ──────┼──► synthesize ──► ranked report
 (GitHub API) ├─ test_agent ──────┤     (merge + sort by severity)
              └─ style_agent ─────┘
```

## Stack

| Layer | Tech |
|---|---|
| Orchestration | LangGraph (parallel fan-out / fan-in) |
| LLM | Groq, `openai/gpt-oss-120b` by default (`GROQ_MODEL`) |
| API | FastAPI with Server-Sent Events streaming |
| Storage | PostgreSQL (review history), Redis (1-hour cache + rate limits) |
| Frontend | Next.js 16, React 19, Tailwind 4, Framer Motion |
| Infra | Docker, docker-compose |

## Run locally

```bash
cp .env.example .env              # add GITHUB_TOKEN and GROQ_API_KEY
docker compose up -d --build      # backend :8002, PostgreSQL, Redis

cd frontend
cp .env.example .env.local
npm install
npm run dev                       # http://localhost:3000
```

Without Docker: `pip install -r requirements.txt` (Python 3.13), then
`uvicorn api.server:app --port 8002`.

## API

| Method | Path | Notes |
|---|---|---|
| `POST` | `/review` | `{"pr_url": "..."}` → full report. 10 req/min per client. |
| `POST` | `/review/stream` | Same, streamed as SSE events per agent. |
| `GET` | `/reviews/recent?limit=10` | Requires `X-API-Key: $ADMIN_API_KEY`. |
| `GET` | `/reviews/stats` | Requires `X-API-Key: $ADMIN_API_KEY`. |
| `GET` | `/health` | Database and cache status. |

## Security

- Per-client rate limiting (SlowAPI, Redis-backed)
- Strict GitHub PR URL validation (blocks path traversal into the GitHub API)
- 1 MB request body cap; security headers (CSP, HSTS, nosniff, frame-deny)
- CORS restricted to `ALLOWED_ORIGINS`; admin endpoints fail closed without `ADMIN_API_KEY`
- Container runs as a non-root user; internal errors are never returned to clients

## Reliability

- A failed agent is reported as **incomplete**, never as a clean PR; incomplete reports aren't cached.
- Groq's free tier allows 8k tokens/min, shared by the four agents — calls use low reasoning
  effort and retry on 429 (honouring `retry-after`).

## Tests

```bash
python -m unittest discover tests
```

## Known limits

- Public pull requests only; diffs beyond 8,000 characters are truncated.
- Findings are AI-generated — a first pass, not a verdict.
