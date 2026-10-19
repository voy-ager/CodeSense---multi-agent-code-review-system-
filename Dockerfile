# Build stage — install dependencies in a clean layer
FROM python:3.13-slim AS builder

WORKDIR /app

# Install gcc needed by asyncpg to compile its C extensions
RUN apt-get update && apt-get install -y gcc && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt


# Runtime stage — copy installed packages and app code
FROM python:3.13-slim

WORKDIR /app

# Copy installed Python packages from builder
COPY --from=builder /usr/local/lib/python3.13/site-packages /usr/local/lib/python3.13/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Run as an unprivileged user — a compromised process can't modify the image or install anything
RUN useradd --uid 1000 --no-create-home --shell /usr/sbin/nologin app

# Copy application code (owned by root, so the app user can read but not modify it)
COPY . .

USER 1000

# Expose the API port
EXPOSE 8002

# Production uvicorn settings
# --workers 1: concurrency comes from async I/O. One process keeps the per-PR
#   single-flight and the LLM review queue global; the bottleneck is Groq, not CPU.
# --proxy-headers: take the client IP from X-Forwarded-For, otherwise every user behind
#   Render's proxy shares one rate-limit bucket. Only safe because the container is
#   reachable solely through the platform proxy (docker-compose dev doesn't use this CMD).
# h11 + 16KB cap: rejects oversized headers (httptools has no limit).
# --limit-concurrency: held-open (slowloris) connections get 503s past 100 instead of
#   exhausting the server; full slowloris protection comes from the platform proxy.
CMD ["uvicorn", "api.server:app", "--host", "0.0.0.0", "--port", "8002", "--workers", "1", "--proxy-headers", "--forwarded-allow-ips", "*", "--http", "h11", "--h11-max-incomplete-event-size", "16384", "--limit-concurrency", "100", "--no-server-header"]