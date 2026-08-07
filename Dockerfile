# Build stage — install dependencies in a clean layer
FROM python:3.11-slim AS builder

WORKDIR /app

# Install gcc needed by asyncpg to compile its C extensions
RUN apt-get update && apt-get install -y gcc && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt


# Runtime stage — copy installed packages and app code
FROM python:3.11-slim

WORKDIR /app

# Copy installed Python packages from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code
COPY . .

# Expose the API port
EXPOSE 8002

# Use uvicorn with multiple workers in production
# --workers 2: handle concurrent requests without blocking
CMD ["uvicorn", "api.server:app", "--host", "0.0.0.0", "--port", "8002", "--workers", "2"]