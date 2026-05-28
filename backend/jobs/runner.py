"""Thin async runner for executor tool calls."""

from __future__ import annotations

from typing import Any, Awaitable, Callable

from backend.agent.memory import AgentSession
from backend.config import Settings
from backend.executor.credibility import assess_credibility
from backend.executor.extract import extract_structured_data
from backend.executor.navigate import navigate_to_url

NavigateCallable = Callable[..., Awaitable[Any]]
ExtractCallable = Callable[..., Awaitable[Any]]
AssessCallable = Callable[..., Awaitable[Any]]


class ResearchRunner:
    """Minimal runner that can dispatch implemented executor tools."""

    def __init__(
        self,
        settings: Settings,
        *,
        navigate: NavigateCallable | None = None,
        extract: ExtractCallable | None = None,
        assess: AssessCallable | None = None,
    ) -> None:
        self._settings = settings
        self._navigate = navigate or navigate_to_url
        self._extract = extract or extract_structured_data
        self._assess = assess or assess_credibility

    async def execute_tool_call(
        self,
        *,
        name: str,
        arguments: dict[str, Any],
        session: AgentSession,
    ) -> dict[str, Any]:
        """Execute a supported tool call and update session state."""
        if not session.can_continue(
            max_steps=self._settings.max_steps_per_job,
            max_tokens=self._settings.max_tokens_per_job,
        ):
            session.finalize("max_steps")
            raise RuntimeError("session_cannot_continue")

        if name == "navigate_to_url":
            result = await self._navigate(
                self._settings,
                url=arguments["url"],
                wait_for=arguments.get("wait_for"),
                fingerprint_seed=arguments.get("fingerprint_seed"),
            )
            session.increment_step()
            session.register_source(result.final_url)
            if result.detection_blocked:
                session.add_detection_event(url=result.final_url, reason=result.blocked_reason or "detection_blocked")
            return result.to_dict()

        if name == "extract_structured_data":
            result = await self._extract(
                self._settings,
                selector=arguments["selector"],
                extraction_goal=arguments["extraction_goal"],
                output_schema=arguments.get("output_schema"),
            )
            session.increment_step()
            return result.to_dict()

        if name == "assess_credibility":
            result = await self._assess(
                self._settings,
                url=arguments["url"],
                content_snippet=arguments["content_snippet"],
            )
            session.increment_step()
            return result.to_dict()

        raise NotImplementedError(f"unsupported_tool:{name}")
