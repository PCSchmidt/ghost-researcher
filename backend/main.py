"""FastAPI application entrypoint for GhostResearcher."""

from __future__ import annotations

from collections.abc import Callable
from typing import Mapping

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.api import create_health_router, create_research_router
from backend.config import Settings
from backend.executor.browser import BrowserHealth
from backend.api.research import ResearchOrchestratorLike
from backend.persistence import ResearchRepository


def create_app(
    env: Mapping[str, str] | None = None,
    *,
    browser_health_resolver: Callable[[], BrowserHealth] | None = None,
    research_orchestrator: ResearchOrchestratorLike | None = None,
    research_repository: ResearchRepository | None = None,
) -> FastAPI:
    """Build the FastAPI app with environment-backed settings."""
    settings = Settings.from_env(env)
    app = FastAPI(title="GhostResearcher API", version="0.1.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_allowed_origins,
        allow_origin_regex=r"https://.*\.vercel\.app",
        allow_credentials=False,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["*"],
    )
    app.include_router(create_health_router(settings, browser_health_resolver=browser_health_resolver))
    app.include_router(
        create_research_router(
            settings,
            orchestrator=research_orchestrator,
            repository=research_repository,
        )
    )
    app.state.settings = settings
    return app


app = create_app()
