"""FastAPI application entrypoint for GhostResearcher."""

from __future__ import annotations

import logging
import sys
from collections.abc import Callable
from typing import Mapping

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.api import create_health_router, create_research_router
from backend.config import Settings
from backend.executor.browser import BrowserHealth
from backend.api.research import ResearchOrchestratorLike
from backend.persistence import JsonFileResearchRepository, ResearchRepository


def _configure_logging(level: str) -> None:
    """Attach a stderr handler to the ghostresearcher namespace.

    Without this, application tracebacks (e.g. a failed research run) fall to
    Python's last-resort handler, which uvicorn's logging config can suppress —
    leaving production 500s undiagnosable. We own this namespace explicitly.
    """
    app_logger = logging.getLogger("ghostresearcher")
    app_logger.setLevel(getattr(logging, level.upper(), logging.INFO))
    if not any(getattr(h, "_ghostresearcher", False) for h in app_logger.handlers):
        handler = logging.StreamHandler(sys.stderr)
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
        handler._ghostresearcher = True  # type: ignore[attr-defined]
        app_logger.addHandler(handler)
    app_logger.propagate = False


def create_app(
    env: Mapping[str, str] | None = None,
    *,
    browser_health_resolver: Callable[[], BrowserHealth] | None = None,
    research_orchestrator: ResearchOrchestratorLike | None = None,
    research_repository: ResearchRepository | None = None,
) -> FastAPI:
    """Build the FastAPI app with environment-backed settings."""
    settings = Settings.from_env(env)
    _configure_logging(settings.log_level)
    app = FastAPI(title="GhostResearcher API", version="0.1.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_allowed_origins,
        allow_origin_regex=r"https://.*\.vercel\.app",
        allow_credentials=False,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["*"],
    )
    # Durable reports: when REPORTS_DB_PATH is set (a Railway volume in production),
    # persist jobs to a JSON file so shareable permalinks and the /reports list
    # survive redeploys. Otherwise the in-memory repo (the router default) is used,
    # which keeps tests and local runs dependency-free.
    if research_repository is None and settings.reports_db_path:
        research_repository = JsonFileResearchRepository(settings.reports_db_path)
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
