# Multi-stage build — frontend in Node, backend in Python, one image.
#
# Build context is the backend/ dir, but we need the frontend sources too.
# We handle that in docker-compose / az acr build by passing the repo root
# as context; see docs/deployment.md. The Dockerfile therefore expects:
#
#   /build-ctx/web/backend/   (this directory)
#   /build-ctx/web/frontend/  (Vite app — sources)

# ---------- Stage 1: frontend ----------
FROM node:20-alpine AS frontend

WORKDIR /build

# Copy manifest first for better layer caching
COPY web/frontend/package.json web/frontend/package-lock.json ./
RUN npm ci --no-audit --no-fund

# Copy the rest of the frontend sources and build
COPY web/frontend ./
RUN npm run build


# ---------- Stage 2: backend + static ----------
FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PORT=8001 \
    FLOWCASE_WEB_STATIC_DIR=/app/static

WORKDIR /app

# Backend deps + source
COPY web/backend/pyproject.toml web/backend/README.md ./
COPY web/backend/src ./src

RUN pip install --upgrade pip && pip install .

# Frontend dist
COPY --from=frontend /build/dist /app/static

# Eval gold dataset — runner.py looks for /app/gold.yaml first
COPY tests/eval/gold.yaml /app/gold.yaml

# Non-root user
RUN useradd --create-home --shell /usr/sbin/nologin appuser \
    && chown -R appuser:appuser /app
USER appuser

EXPOSE 8001

HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request,sys; \
        sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8001/health',timeout=2).status==200 else 1)"

CMD ["uvicorn", "flowcase_web.main:app", "--host", "0.0.0.0", "--port", "8001"]
