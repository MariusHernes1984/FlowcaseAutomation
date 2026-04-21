# Flowcase MCP — Azure Container Apps image
#
# Runs the server in streamable-HTTP mode on port 8000. Secrets and the
# availability workbook are NOT baked into the image:
#
#   FLOWCASE_API_KEY         — Flowcase ServiceHub subscription key (Key Vault)
#   FLOWCASE_MCP_API_KEY     — Shared secret for X-API-Key header auth (Key Vault)
#   FLOWCASE_AVAILABILITY_PATH  — Path to the workbook (Blob mount, e.g. /data/availability.xlsx)
#
# All three are injected at runtime via Container Apps env + secrets.

FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    FLOWCASE_MCP_TRANSPORT=streamable-http \
    PORT=8000

WORKDIR /app

# Copy only the files pip needs to build the wheel first — keeps layers cached.
COPY pyproject.toml README.md ./
COPY src ./src

RUN pip install --upgrade pip && pip install ".[http]"

# Non-root user for runtime (Container Apps best practice).
RUN useradd --create-home --shell /usr/sbin/nologin appuser \
    && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

# Healthcheck uses the /health endpoint bypassed by the auth middleware.
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request,sys; \
        sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/health',timeout=2).status==200 else 1)"

CMD ["python", "-m", "flowcase_mcp"]
