"""Thin async runner for executor tool calls."""

from __future__ import annotations

from typing import Any, Awaitable, Callable

from backend.agent.memory import AgentSession
from backend.config import Settings
from backend.executor.credibility import assess_credibility
from backend.executor.extract import extract_structured_data
from backend.executor.navigate import navigate_to_url
from backend.executor.search import web_search

NavigateCallable = Callable[..., Awaitable[Any]]
ExtractCallable = Callable[..., Awaitable[Any]]
AssessCallable = Callable[..., Awaitable[Any]]
SearchCallable = Callable[..., Awaitable[Any]]


class ResearchRunner:
    """Minimal runner that can dispatch implemented executor tools."""

    def __init__(
        self,
        settings: Settings,
        *,
        navigate: NavigateCallable | None = None,
        extract: ExtractCallable | None = None,
        assess: AssessCallable | None = None,
        search: SearchCallable | None = None,
    ) -> None:
        self._settings = settings
        self._navigate = navigate or navigate_to_url
        self._extract = extract or extract_structured_data
        self._assess = assess or assess_credibility
        self._search = search or web_search

    def _corroborating_evidence(self, session: AgentSession, *, current_url: str) -> tuple[list[str], list[str]]:
        """Return prior evidence signals that can strengthen credibility scoring."""
        sources: list[str] = []
        claims: list[str] = []
        seen_sources: set[str] = set()
        seen_claims: set[str] = set()
        for record in session.evidence_records:
            if record.url == current_url or record.evidence_type not in {"assessed", "extracted"}:
                continue
            if record.url not in seen_sources:
                seen_sources.add(record.url)
                sources.append(record.url)
            for claim in record.claims:
                if claim not in seen_claims:
                    seen_claims.add(claim)
                    claims.append(claim)
        return sources, claims

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

        if name == "web_search":
            result = await self._search(
                self._settings,
                query=arguments["query"],
                num_results=arguments.get("num_results", 5),
                existing_urls=session.sources_visited.union(session.source_candidates),
            )
            session.increment_step()
            session.record_search_query(result.query)
            session.add_source_candidates([item["url"] for item in result.to_dict()["results"]])
            return result.to_dict()

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
                selector=arguments.get("selector", "body"),
                extraction_goal=arguments["extraction_goal"],
                output_schema=arguments.get("output_schema"),
            )
            session.increment_step()
            current_url = session.current_source_url or ""
            if current_url and result.text_excerpt:
                session.add_evidence(
                    url=current_url,
                    title=current_url,
                    claims=[result.text_excerpt],
                    credibility_score=0.5,
                    evidence_type="extracted",
                )
            return result.to_dict()

        if name == "assess_credibility":
            current_url = str(arguments["url"])
            corroborating_sources = arguments.get("corroborating_sources")
            corroborating_claims = arguments.get("corroborating_claims")
            if not isinstance(corroborating_sources, list) or not isinstance(corroborating_claims, list):
                derived_sources, derived_claims = self._corroborating_evidence(session, current_url=current_url)
                if not isinstance(corroborating_sources, list):
                    corroborating_sources = derived_sources
                if not isinstance(corroborating_claims, list):
                    corroborating_claims = derived_claims
            result = await self._assess(
                self._settings,
                url=current_url,
                content_snippet=arguments["content_snippet"],
                corroborating_sources=[str(url) for url in corroborating_sources],
                corroborating_claims=[str(claim) for claim in corroborating_claims],
            )
            session.increment_step()
            session.add_evidence(
                url=result.url,
                title=result.url,
                claims=[arguments["content_snippet"]],
                credibility_score=result.score,
            )
            return result.to_dict()

        if name == "finalize_report":
            confidence = arguments.get("confidence")
            sources_used = arguments.get("sources_used")
            termination_reason = str(arguments.get("termination_reason", "sufficient_coverage"))
            if not isinstance(confidence, (int, float)) or isinstance(confidence, bool):
                raise ValueError("invalid_confidence")
            if confidence < 0 or confidence > 1:
                raise ValueError("invalid_confidence")
            if not isinstance(sources_used, list):
                raise ValueError("invalid_sources_used")
            evidence_urls = {record.url for record in session.evidence_records}
            assessed_urls = session.evidence_urls_by_type("assessed")
            unsupported_sources = [str(url) for url in sources_used if str(url) not in evidence_urls]
            if unsupported_sources:
                raise ValueError("unsupported_finalize_source")
            if termination_reason == "sufficient_coverage":
                unassessed_sources = [str(url) for url in sources_used if str(url) not in assessed_urls]
                if unassessed_sources:
                    raise ValueError("unassessed_finalize_source")
            if termination_reason == "sufficient_coverage" and not sources_used:
                raise ValueError("no_sources_selected")
            session.increment_step()
            session.finalize(termination_reason)
            return {
                "accepted": True,
                "queued_for_synthesis": termination_reason == "sufficient_coverage" and bool(sources_used),
                "termination_reason": termination_reason,
                "confidence": round(float(confidence), 3),
                "sources_used": [str(url) for url in sources_used],
            }

        raise NotImplementedError(f"unsupported_tool:{name}")
