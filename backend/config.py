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


def _parse_csv(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


@dataclass(frozen=True, slots=True)
class Settings:
    openrouter_api_key: str | None
    openrouter_base_url: str
    openrouter_app_title: str
    openrouter_http_referer: str
    default_planner_model: str
    fallback_planner_model: str
    default_synthesizer_model: str
    fallback_synthesizer_model: str
    anthropic_api_key: str | None
    cloak_cdp_url: str
    database_url: str | None
    redis_url: str | None
    search_provider: str
    search_api_key: str | None
    search_api_url: str
    proxy_url: str | None
    proxy_user: str | None
    proxy_pass: str | None
    max_steps_per_job: int
    max_tokens_per_job: int
    max_model_cost_per_job_usd: float
    warn_model_cost_per_job_usd: float
    scrape_enabled: bool
    log_level: str
    next_public_api_url: str | None
    cors_allowed_origins: list[str]
    job_time_budget_seconds: float = 240.0
    job_hard_timeout_seconds: float = 330.0

    @classmethod
    def from_env(cls, env: Mapping[str, str] | None = None) -> "Settings":
        source = env if env is not None else environ
        scrape_enabled = _parse_bool(source.get("SCRAPE_ENABLED", "true"), default=True)
        return cls(
            openrouter_api_key=source.get("OPENROUTER_API_KEY"),
            openrouter_base_url=source.get("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"),
            openrouter_app_title=source.get("OPENROUTER_APP_TITLE", "GhostResearcher"),
            openrouter_http_referer=source.get("OPENROUTER_HTTP_REFERER", "http://localhost:8000"),
            default_planner_model=source.get("DEFAULT_PLANNER_MODEL", "deepseek/deepseek-v4-flash"),
            fallback_planner_model=source.get("FALLBACK_PLANNER_MODEL", "deepseek/deepseek-v4-pro"),
            default_synthesizer_model=source.get("DEFAULT_SYNTHESIZER_MODEL", "deepseek/deepseek-v4-flash"),
            fallback_synthesizer_model=source.get("FALLBACK_SYNTHESIZER_MODEL", "moonshotai/kimi-k2.6"),
            anthropic_api_key=source.get("ANTHROPIC_API_KEY"),
            cloak_cdp_url=source.get("CLOAK_CDP_URL", "http://localhost:9222"),
            database_url=source.get("DATABASE_URL"),
            redis_url=source.get("REDIS_URL"),
            search_provider=source.get("SEARCH_PROVIDER", "deterministic"),
            search_api_key=source.get("SEARCH_API_KEY") or source.get("GHOST_RESEARCHER_API_KEY"),
            search_api_url=source.get("SEARCH_API_URL", "https://api.search.brave.com/res/v1/web/search"),
            proxy_url=source.get("PROXY_URL"),
            proxy_user=source.get("PROXY_USER"),
            proxy_pass=source.get("PROXY_PASS"),
            max_steps_per_job=int(source.get("MAX_STEPS_PER_JOB", "20")),
            max_tokens_per_job=int(source.get("MAX_TOKENS_PER_JOB", "125000")),
            max_model_cost_per_job_usd=float(source.get("MAX_MODEL_COST_PER_JOB_USD", "0.15")),
            warn_model_cost_per_job_usd=float(source.get("WARN_MODEL_COST_PER_JOB_USD", "0.02")),
            scrape_enabled=scrape_enabled,
            log_level=source.get("LOG_LEVEL", "INFO"),
            next_public_api_url=source.get("NEXT_PUBLIC_API_URL"),
            cors_allowed_origins=_parse_csv(
                source.get("CORS_ALLOWED_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000")
            ),
            job_time_budget_seconds=float(source.get("JOB_TIME_BUDGET_SECONDS", "240")),
            job_hard_timeout_seconds=float(source.get("JOB_HARD_TIMEOUT_SECONDS", "330")),
        )
