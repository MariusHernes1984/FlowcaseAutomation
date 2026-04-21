"""FastAPI entry point — wires auth, agents and (later) chat routers."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from flowcase_web import storage
from flowcase_web.agents import ensure_seed_agents
from flowcase_web.agents import router as agents_router
from flowcase_web.auth import router as auth_router
from flowcase_web.auth.bootstrap import ensure_admin
from flowcase_web.chats import router as chats_router
from flowcase_web.config import get_settings

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    settings = get_settings()
    handle = await storage.connect(settings)
    try:
        await ensure_admin(handle, settings)
        await ensure_seed_agents(handle)
    except Exception:
        logger.exception("Startup bootstrap failed — app will keep running")
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

    app.include_router(auth_router, prefix="/auth", tags=["auth"])
    app.include_router(agents_router, prefix="/agents", tags=["agents"])
    app.include_router(chats_router, prefix="/chats", tags=["chats"])
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
