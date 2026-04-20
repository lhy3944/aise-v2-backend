# ---- Build stage ----
FROM python:3.14-rc-slim AS builder

WORKDIR /app

RUN pip install uv

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

COPY . .
RUN uv sync --frozen --no-dev

# ---- Run stage ----
FROM python:3.14-rc-slim AS runner

WORKDIR /app

COPY --from=builder /app /app

ENV PATH="/app/.venv/bin:$PATH"

EXPOSE 8081

COPY <<'ENTRYPOINT' /app/entrypoint.sh
#!/bin/sh
set -e

echo "=== Running Alembic migrations ==="
if ! alembic upgrade head 2>&1; then
  echo "WARNING: alembic upgrade failed. Attempting stamp head..."
  alembic stamp head 2>&1 || echo "WARNING: alembic stamp also failed. Continuing..."
fi

echo "=== Starting server ==="
exec uvicorn src.main:app --host 0.0.0.0 --port 8081
ENTRYPOINT

RUN chmod +x /app/entrypoint.sh

CMD ["/app/entrypoint.sh"]
