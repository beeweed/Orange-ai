"""Application configuration.

Centralised, validated settings loaded from environment variables with
sensible production defaults. Secrets (API keys) are NEVER hard-coded here -
they are supplied per-request by the client via the settings UI, or via env.
"""
from __future__ import annotations

from functools import lru_cache
from typing import List

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Strongly-typed runtime configuration."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # ---- Server ----
    app_name: str = "Vibe Coder Agent API"
    app_version: str = "1.0.0"
    host: str = "0.0.0.0"
    port: int = 8000
    log_level: str = "INFO"

    # ---- CORS ----
    # Permissive by default so the Vite dev frontend (any origin/tunnel host)
    # can reach the backend. Tighten in a hardened deployment.
    cors_origins: List[str] = Field(default_factory=lambda: ["*"])

    # ---- Agent ----
    max_iterations: int = 1000
    # E2B sandbox lifetime in seconds (1 hour as required).
    sandbox_timeout_seconds: int = 3600

    # ---- Provider base URLs (OpenAI-compatible) ----
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    nvidia_base_url: str = "https://integrate.api.nvidia.com/v1"

    # Optional referer/title headers OpenRouter recommends.
    openrouter_referer: str = "https://vibe-coder.app"
    openrouter_title: str = "Vibe Coder Agent"

    # HTTP client timeouts (seconds)
    http_connect_timeout: float = 30.0
    http_read_timeout: float = 600.0

    # ---- Web retrieval tools ----
    max_search_results: int = 15
    search_provider: str = "tavily"
    fetch_provider: str = "firecrawl"
    tavily_search_url: str = "https://api.tavily.com/search"
    firecrawl_scrape_url: str = "https://api.firecrawl.dev/v2/scrape"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return a cached singleton Settings instance."""
    return Settings()
