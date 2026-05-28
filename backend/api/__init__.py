"""API route modules for GhostResearcher."""

from .health import create_health_router
from .research import create_research_router

__all__ = ["create_health_router", "create_research_router"]

