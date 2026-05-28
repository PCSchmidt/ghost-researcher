"""Environment-backed runtime settings for GhostResearcher."""

from __future__ import annotations

from dataclasses import dataclass
from os import environ
from typing import Mapping


def _parse_bool(value: str, *, default: bool) -> bool:
    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    return default


@dataclass(frozen=True, slots=True)
class Settings:
    anthropic_api_key: str | None
    cloak_cdp_url: str
    database_url: str | None
    redis_url: str | None
    proxy_url: str | None
    proxy_user: str | None
    proxy_pass: str | None
    max_steps_per_job: int
    max_tokens_per_job: int
    scrape_enabled: bool
    log_level: str
    next_public_api_url: str | None

    @classmethod
    def from_env(cls, env: Mapping[str, str] | None = None) -> "Settings":
        source = env if env is not None else environ
        scrape_enabled = _parse_bool(source.get("SCRAPE_ENABLED", "true"), default=True)
        return cls(
            anthropic_api_key=source.get("ANTHROPIC_API_KEY"),
            cloak_cdp_url=source.get("CLOAK_CDP_URL", "http://localhost:9222"),
            database_url=source.get("DATABASE_URL"),
            redis_url=source.get("REDIS_URL"),
            proxy_url=source.get("PROXY_URL"),
            proxy_user=source.get("PROXY_USER"),
            proxy_pass=source.get("PROXY_PASS"),
            max_steps_per_job=int(source.get("MAX_STEPS_PER_JOB", "20")),
            max_tokens_per_job=int(source.get("MAX_TOKENS_PER_JOB", "50000")),
            scrape_enabled=scrape_enabled,
            log_level=source.get("LOG_LEVEL", "INFO"),
            next_public_api_url=source.get("NEXT_PUBLIC_API_URL"),
        )
