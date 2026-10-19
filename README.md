# CodeSense

Multi-agent AI code review. Paste a GitHub pull request URL; four specialist agents review
**security**, **performance**, **test coverage**, and **style** in parallel and return one
severity-ranked report with a concrete fix for every finding. Rule-based checks run
alongside them for the problems AI reviewers miss or can be talked out of.

```
              ┌─ security_agent ──┐
              ├─ perf_agent ──────┤
ingest_diff ──┼─ test_agent ──────┼──► synthesize ──► ranked report
 (GitHub API) ├─ style_agent ─────┤     (validate, de-duplicate, sort by severity)
              └─ static_scan ─────┘
                 (rules, no LLM)
```

## Why the rule-based checks

| Problem (2025–26) | What CodeSense does |
|---|---|
| AI-assisted commits leak secrets ~2× more often than average ([GitGuardian 2026](https://gitguardian.com/state-of-secrets-sprawl-report-2026)); GhostCommit hides secrets as integer lists | Detects provider keys, private keys and literal credentials on added lines — including integer-encoded secrets — and redacts them in the report |
| **Slopsquatting**: AI tools invent package names that attackers then register | Checks every package added to `requirements*.txt` / `package.json` against PyPI and npm: flags names that don't exist and packages under 30 days old |
| Prompt injection hijacking AI review bots ([CSA research](https://labs.cloudsecurityalliance.org/research/csa-research-note-comment-control-github-prompt-injection-20/)) | The diff is passed to the model as nonce-fenced untrusted data; rules flag text aimed at AI reviewers |
| Trojan Source: bidi / zero-width characters make code read differently than it runs | Flags hidden Unicode on added lines (CodeSense's own test suite runs the same check on this repo) |
| Noisy, malformed AI output | Every finding is schema-validated (Pydantic), capped per agent and de-duplicated |

## Stack

| Layer | Tech |
|---|---|
| Orchestration | LangGraph (parallel fan-out / fan-in) |
| LLM | Groq, `openai/gpt-oss-120b` by default (`GROQ_MODEL`) |
| API | FastAPI with Server-Sent Events streaming |
| Storage | PostgreSQL (review history), Redis (1-hour cache + rate limits) |
| Frontend | Next.js 16, React 19, Tailwind 4, Framer Motion |
| Integrations | MCP server (`review_pull_request` tool) |
| Infra | Docker, docker-compose, GitHub Actions CI |

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

## Use it from your editor (MCP)

```json
{
  "mcpServers": {
    "codesense": {
      "command": "/path/to/codesense/.venv/bin/python",
      "args": ["/path/to/codesense/mcp_server.py"]
    }
  }
}
```

Works with Claude Desktop, Cursor and VS Code. `GITHUB_TOKEN` and `GROQ_API_KEY` are read
from the environment or the repo's `.env`.

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
- Header size capped (16 KB), concurrent connections capped, no `Server` header;
  set `EXPOSE_DOCS=false` in production to hide `/docs` and `/openapi.json`
- Audited with `bandit` (0 issues), `pip-audit` (0 known vulnerabilities) and
  `npm audit --omit=dev` (0); see the attack suite in `tests/test_attacks.py`

## Reliability

- A failed agent is reported as **incomplete**, never as a clean PR; incomplete reports aren't cached.
- The cache is keyed by PR URL **and head commit**, so a new push always gets a fresh review.
- Groq's free tier allows 8k tokens/min, shared by the four agents — calls use low reasoning
  effort and retry on 429 (honouring `retry-after`).

## Tests

```bash
python -m unittest discover tests        # unit, scanner, MCP and attack tests
cd frontend && npm run test:e2e          # browser tests (API mocked), desktop + mobile
E2E_LIVE=1 npm run test:e2e              # plus a real review against the running stack
```

CI (`.github/workflows/ci.yml`) runs all of the above plus bandit, pip-audit, npm audit,
a production build and a non-root Docker image check on every push.

## Known limits

- Public pull requests only. The AI agents read the first 8,000 characters of a diff;
  rule-based checks read all of it (up to 2 MB).
- Slowloris-style slow connections are bounded but not fully prevented by uvicorn —
  deploy behind a reverse proxy (Render/Vercel provide one).
- `braces` (dev-only, via the ESLint plugin) has an advisory with no patched release yet;
  it never runs in production.
- Findings are AI-generated — a first pass, not a verdict.
