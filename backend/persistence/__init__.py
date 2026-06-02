"""Persistence repositories for GhostResearcher."""

from backend.persistence.repository import InMemoryResearchRepository, JsonFileResearchRepository, ResearchRepository

__all__ = ["InMemoryResearchRepository", "JsonFileResearchRepository", "ResearchRepository"]
