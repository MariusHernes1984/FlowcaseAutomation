"""FastAPI entry point.

Stage-1 scaffolding: only a ``/health`` endpoint so the image builds and
deploys cleanly. Routers for ``/auth``, ``/agents``, ``/chat`` are added
in the next iteration.
"""

from __future__ import annotations

from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from flowcase_web.config import get_settings


@asynccontextmanager
async def lifespan(_app: FastAPI):
    # Placeholder for Cosmos client init + admin bootstrap.
    yield


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

    # TODO(phase-2): register auth/agents/chat routers
    # from flowcase_web.auth.router import router as auth_router
    # app.include_router(auth_router, prefix="/auth", tags=["auth"])

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
