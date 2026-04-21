"""Runtime configuration loaded from environment variables.

Every backend module imports from here rather than reading ``os.environ``
directly — keeps secrets in one place and makes unit tests easier.
"""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # -- App basics --------------------------------------------------------
    app_name: str = "flowcase-web"
    environment: str = Field(default="dev", description="dev / test / prod")
    cors_origins: list[str] = Field(
        default_factory=lambda: ["http://localhost:5173"],
        description="Allowed frontend origins.",
    )

    # -- Admin bootstrap ---------------------------------------------------
    admin_email: str = Field(default="admin@atea.no", description="Email of the bootstrap admin user.")
    admin_password: str = Field(
        default="",
        description=(
            "Plain-text password for the bootstrap admin. Set via secret "
            "in Container App. Hashed on first boot, then ignored if the "
            "user already exists."
        ),
    )

    # -- Auth / JWT --------------------------------------------------------
    jwt_secret: str = Field(
        default="",
        description="HMAC key for signing access tokens. Set via Key Vault.",
    )
    jwt_algorithm: str = "HS256"
    access_token_ttl_minutes: int = 30
    refresh_token_ttl_days: int = 7

    # -- Cosmos DB ---------------------------------------------------------
    cosmos_endpoint: str = Field(
        default="https://localhost:8081",
        description="Cosmos account URL (serverless SQL API).",
    )
    cosmos_key: str = Field(default="", description="Master key (or use managed identity).")
    cosmos_database: str = "flowcase"
    cosmos_container_users: str = "users"
    cosmos_container_agents: str = "agents"
    cosmos_container_chats: str = "chats"

    # -- LLM (Azure OpenAI / Foundry) --------------------------------------
    azure_openai_endpoint: str = ""
    azure_openai_api_key: str = ""
    azure_openai_api_version: str = "2024-10-21"
    default_llm_deployment: str = "gpt-5.4-mini"

    # -- Flowcase MCP (remote streamable-HTTP) -----------------------------
    mcp_url: str = ""
    mcp_api_key: str = ""


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings instance (cheap to call many times)."""
    return Settings()
