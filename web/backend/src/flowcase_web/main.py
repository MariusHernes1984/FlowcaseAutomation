"""FastAPI entry point — wires auth, agents and chat routers, and serves
the built React SPA from ``/`` so a single Container App hosts both."""

from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

import uvicorn
from fastapi import APIRouter, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from flowcase_web import storage
from flowcase_web.agents import ensure_seed_agents
from flowcase_web.agents import router as agents_router
from flowcase_web.auth import router as auth_router
from flowcase_web.auth.bootstrap import ensure_admin
from flowcase_web.chats import router as chats_router
from flowcase_web.config import get_settings
from flowcase_web.eval import router as eval_router
from flowcase_web.reference import router as reference_router

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    import asyncio

    settings = get_settings()
    handle = await storage.connect(settings)
    try:
        await ensure_admin(handle, settings)
        await ensure_seed_agents(handle)
    except Exception:
        logger.exception("Startup bootstrap failed — app will keep running")

    # Fire-and-forget: warm the MCP server's caches (countries, skill
    # taxonomy, data_export) so the first real chat doesn't pay the
    # 10–15 s cold-cache cost. If it fails, the next real call still
    # works — just without the warm-up boost.
    async def _warmup() -> None:
        if not settings.mcp_url or not settings.mcp_api_key:
            return
        try:
            from flowcase_web.mcp_client import FlowcaseMcpClient

            client = FlowcaseMcpClient(settings.mcp_url, settings.mcp_api_key)
            # Cheap calls that hydrate the heavy caches server-side.
            await client.call_tool(
                "flowcase_list_offices",
                {"params": {"response_format": "json"}},
            )
            await client.call_tool(
                "flowcase_list_skills",
                {"params": {"limit": 1, "response_format": "json"}},
            )
            logger.info("MCP warm-up finished")
        except Exception:
            logger.exception("MCP warm-up failed — continuing anyway")

    asyncio.create_task(_warmup())

    yield
    await storage.close()


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="Flowcase Web",
        version="0.1.0",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/health")
    async def healthcheck() -> dict[str, str]:
        return {"status": "ok", "env": settings.environment}

    # All business endpoints live under /api so the SPA can own everything
    # else (client-side routing) without collisions.
    api = APIRouter(prefix="/api")
    api.include_router(auth_router, prefix="/auth", tags=["auth"])
    api.include_router(agents_router, prefix="/agents", tags=["agents"])
    api.include_router(chats_router, prefix="/chats", tags=["chats"])
    api.include_router(reference_router, prefix="/reference", tags=["reference"])
    api.include_router(eval_router, prefix="/admin/evals", tags=["admin-evals"])
    app.include_router(api)

    # Serve the built React SPA when the dist directory is present.
    # In local dev (uvicorn --reload) the dist folder usually doesn't exist
    # and Vite handles the UI; skip mounting then.
    dist_dir = Path(
        os.environ.get("FLOWCASE_WEB_STATIC_DIR", "/app/static")
    ).resolve()
    if dist_dir.is_dir() and (dist_dir / "index.html").exists():
        assets_dir = dist_dir / "assets"
        if assets_dir.is_dir():
            app.mount(
                "/assets",
                StaticFiles(directory=str(assets_dir)),
                name="assets",
            )

        @app.get("/{path:path}")
        async def spa_fallback(path: str) -> FileResponse:
            # /api/* and /health are declared above, so they take priority.
            candidate = dist_dir / path
            if candidate.is_file():
                return FileResponse(candidate)
            index = dist_dir / "index.html"
            if not index.exists():
                raise HTTPException(status_code=404)
            return FileResponse(index)

    return app


app = create_app()


def main() -> None:
    settings = get_settings()
    uvicorn.run(
        "flowcase_web.main:app",
        host="0.0.0.0",
        port=8001,
        log_level="info",
        reload=settings.environment == "dev",
    )


if __name__ == "__main__":
    main()
