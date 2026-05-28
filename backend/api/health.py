"""Health and readiness endpoints for GhostResearcher."""

from __future__ import annotations

from collections.abc import Callable

from fastapi import APIRouter

from backend.config import Settings
from backend.executor.browser import BrowserHealth, CloakBrowserClient

def _status_from_value(value: str | None, *, configured_label: str = "configured") -> str:
    return configured_label if value else "missing"


def build_health_payload(settings: Settings) -> dict[str, object]:
    """Create a truthful liveness and configuration snapshot for the backend."""
    cloak_status = "configured" if settings.scrape_enabled else "disabled"
    return {
        "status": "ok",
        "service": "ghostresearcher-api",
        "version": "0.1.0",
        "dependencies": {
            "anthropic": _status_from_value(settings.anthropic_api_key),
            "cloak_cdp": cloak_status,
            "database": _status_from_value(settings.database_url),
            "redis": _status_from_value(settings.redis_url),
        },
        "limits": {
            "max_steps_per_job": settings.max_steps_per_job,
            "max_tokens_per_job": settings.max_tokens_per_job,
        },
    }


def create_health_router(
    settings: Settings,
    *,
    browser_health_resolver: Callable[[], BrowserHealth] | None = None,
) -> APIRouter:
    """Create health endpoints bound to the current app settings."""
    router = APIRouter(tags=["health"])
    resolver = browser_health_resolver or (lambda: CloakBrowserClient(settings).healthcheck())

    @router.get("/health")
    def healthcheck() -> dict[str, object]:
        payload = build_health_payload(settings)
        payload["dependencies"]["cloak_cdp"] = resolver().to_dict()
        return payload

    return router


__all__ = ["build_health_payload", "create_health_router"]
