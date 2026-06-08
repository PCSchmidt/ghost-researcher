"""Repeatable benchmark evaluation harness for GhostResearcher."""

from __future__ import annotations

import argparse
import asyncio
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Callable

from backend.config import Settings
from backend.executor.browser import BrowserHealth, CloakBrowserClient
from backend.executor.credibility import assess_credibility
from backend.executor.extract import ExtractionResult
from backend.executor.navigate import NavigationResult
from backend.executor.search import SearchResultItem, SearchResults
from backend.jobs.research import PlannerSequenceResult, ResearchOrchestrator
from backend.jobs.runner import ResearchRunner
from backend.synthesizer.schema import ReportValidationError, validate_report_sources

DEFAULT_BENCHMARK_PATH = Path(__file__).with_name("benchmark_prompts.json")
DEFAULT_RESULTS_DIR = Path(__file__).with_name("results")


@dataclass(frozen=True, slots=True)
class BenchmarkPrompt:
    """One benchmark prompt and its scoring expectations."""

    id: str
    prompt: str
    domain: str
    expected_source_types: list[str]
    expected_sources: list[str]
    min_sources: int
    max_steps: int
    eval_criteria: dict[str, Any]
    notes: str

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "BenchmarkPrompt":
        return cls(
            id=_required_string(payload, "id"),
            prompt=_required_string(payload, "prompt"),
            domain=_required_string(payload, "domain"),
            expected_source_types=_string_list(payload, "expected_source_types"),
            expected_sources=_string_list(payload, "expected_sources"),
            min_sources=int(payload.get("min_sources", 1)),
            max_steps=int(payload.get("max_steps", 4)),
            eval_criteria=dict(payload.get("eval_criteria", {})),
            notes=str(payload.get("notes", "")),
        )


def load_benchmark_prompts(path: Path = DEFAULT_BENCHMARK_PATH) -> list[BenchmarkPrompt]:
    """Load benchmark prompts from disk."""
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, list):
        raise ValueError("benchmark_prompts_must_be_list")
    return [BenchmarkPrompt.from_dict(item) for item in payload if isinstance(item, dict)]


async def run_eval_suite(
    *,
    prompts: list[BenchmarkPrompt],
    settings: Settings | None = None,
    mode: str = "offline",
    orchestrator_factory: Callable[[Settings], Any] | None = None,
    browser_healthcheck: Callable[[Settings], BrowserHealth] | None = None,
) -> dict[str, Any]:
    """Run benchmark prompts through the offline or live harness."""
    normalized_mode = mode.strip().lower()
    if normalized_mode not in {"offline", "live"}:
        raise ValueError("invalid_eval_mode")
    active_settings = settings or Settings.from_env({})
    live_environment: dict[str, Any] | None = None
    if normalized_mode == "live":
        if active_settings.search_provider.strip().lower() in {"", "deterministic", "offline"}:
            raise ValueError("live_search_provider_required")
        live_environment = validate_live_environment(
            active_settings,
            browser_healthcheck=browser_healthcheck,
        )
    cases: list[dict[str, Any]] = []
    for prompt in prompts:
        result = await _run_prompt(
            prompt,
            active_settings,
            mode=normalized_mode,
            orchestrator_factory=orchestrator_factory,
        )
        cases.append(score_prompt(prompt, result))

    average_score = round(sum(case["score"] for case in cases) / len(cases), 3) if cases else 0.0
    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "mode": normalized_mode,
        "search_provider": active_settings.search_provider,
        "benchmark_count": len(cases),
        "average_score": average_score,
        "cases": cases,
        "live_environment": live_environment,
    }


def validate_live_environment(
    settings: Settings,
    *,
    browser_healthcheck: Callable[[Settings], BrowserHealth] | None = None,
) -> dict[str, Any]:
    """Validate the configured live services before running a live eval."""
    missing: list[str] = []
    if settings.search_provider.strip().lower() != "brave":
        missing.append("SEARCH_PROVIDER=brave")
    if not settings.search_api_key:
        missing.append("SEARCH_API_KEY")
    if not settings.openrouter_api_key:
        missing.append("OPENROUTER_API_KEY")
    if not settings.cloak_cdp_url:
        missing.append("CLOAK_CDP_URL")
    if not settings.scrape_enabled:
        missing.append("SCRAPE_ENABLED=1")
    if missing:
        raise ValueError("live_environment_missing:" + ", ".join(missing))

    healthcheck = browser_healthcheck or (lambda active_settings: CloakBrowserClient(active_settings).healthcheck(timeout=5.0))
    health = healthcheck(settings)
    if health.status != "ok":
        detail = health.detail or health.status
        raise ValueError(f"live_cloakbrowser_unreachable:{detail}")

    return {
        "search_provider": settings.search_provider,
        "search_api_key": True,
        "openrouter_api_key": True,
        "cloakbrowser": health.to_dict(),
    }


def score_prompt(prompt: BenchmarkPrompt, result: PlannerSequenceResult) -> dict[str, Any]:
    """Score one benchmark result for source coverage and report traceability."""
    report = result.synthesis
    report_text = _report_text(report.to_dict() if report else {})
    sources = report.sources_used if report else sorted(result.session.sources_visited)
    evidence_urls = [record.url for record in result.session.evidence_records]
    expected_matches = _expected_source_matches(prompt.expected_sources, sources)
    metrics = {
        "completed": result.session.termination_reason == "sufficient_coverage",
        "report_generated": report is not None,
        "source_count": len(sources),
        "min_sources": prompt.min_sources,
        "source_count_score": _ratio(len(sources), prompt.min_sources),
        "expected_source_matches": expected_matches,
        "expected_source_score": _ratio(len(expected_matches), max(1, min(prompt.min_sources, len(prompt.expected_sources)))),
        "source_trace_score": _source_trace_score(result),
        "criteria_coverage_score": _criteria_coverage(prompt, report_text),
        "freshness_score": _freshness_score(prompt, report_text),
        "tool_sequence": [decision.tool_call.name for decision in result.decisions if decision.tool_call is not None],
        "termination_reason": result.session.termination_reason,
    }
    score = round(
        (
            (1.0 if metrics["completed"] else 0.0) * 0.2
            + (1.0 if metrics["report_generated"] else 0.0) * 0.15
            + metrics["source_count_score"] * 0.2
            + metrics["expected_source_score"] * 0.15
            + metrics["source_trace_score"] * 0.2
            + metrics["criteria_coverage_score"] * 0.07
            + metrics["freshness_score"] * 0.03
        ),
        3,
    )
    return {
        "id": prompt.id,
        "domain": prompt.domain,
        "prompt": prompt.prompt,
        "score": score,
        "metrics": metrics,
        "sources": sources,
        "evidence_urls": evidence_urls,
        "report": report.to_dict() if report else None,
        "limitations": _limitations(prompt, metrics),
    }


def write_eval_results(payload: dict[str, Any], *, results_dir: Path = DEFAULT_RESULTS_DIR) -> Path:
    """Write an eval result artifact and return its path."""
    results_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    path = results_dir / f"eval_results_{timestamp}.json"
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, sort_keys=True)
        handle.write("\n")
    return path


async def _run_prompt(
    prompt: BenchmarkPrompt,
    settings: Settings,
    *,
    mode: str,
    orchestrator_factory: Callable[[Settings], Any] | None = None,
) -> PlannerSequenceResult:
    if mode == "live":
        orchestrator = orchestrator_factory(settings) if orchestrator_factory else ResearchOrchestrator(settings)
        return await orchestrator.run_sequence(
            prompt.prompt,
            max_steps=min(prompt.max_steps, settings.max_steps_per_job),
            min_sources=prompt.min_sources,
        )

    runner = ResearchRunner(
        settings,
        search=_fake_search(prompt),
        navigate=_fake_navigate(prompt),
        extract=_fake_extract(prompt),
        assess=assess_credibility,
    )
    orchestrator = ResearchOrchestrator(settings, runner=runner)
    return await orchestrator.run_sequence(
        prompt.prompt,
        max_steps=min(prompt.max_steps, settings.max_steps_per_job),
        min_sources=prompt.min_sources,
    )


def _fake_search(prompt: BenchmarkPrompt):
    async def search(settings: Settings, **kwargs: Any) -> SearchResults:
        del settings
        query = str(kwargs["query"])
        num_results = int(kwargs.get("num_results", 5))
        existing_urls = set(kwargs.get("existing_urls") or set())
        items: list[SearchResultItem] = []
        for index, expected_source in enumerate(prompt.expected_sources[:num_results]):
            url = _source_url(expected_source, prompt.id)
            if url in existing_urls:
                continue
            source_type = prompt.expected_source_types[index % len(prompt.expected_source_types)] if prompt.expected_source_types else "web"
            items.append(
                SearchResultItem(
                    title=f"{expected_source} benchmark source",
                    url=url,
                    snippet=f"Benchmark candidate for {query}",
                    source_type=source_type,
                )
            )
        return SearchResults(query=query, results=items, new_result_count=len(items))

    return search


def _fake_navigate(prompt: BenchmarkPrompt):
    async def navigate(settings: Settings, **kwargs: Any) -> NavigationResult:
        del settings
        url = str(kwargs["url"])
        evidence_text = _evidence_text(prompt, url)
        return NavigationResult(
            url=url,
            final_url=url,
            title=f"Benchmark source for {prompt.id}",
            status_code=200,
            content_excerpt=evidence_text,
            links=[],
            detection_blocked=False,
            blocked_reason=None,
            screenshot_path=None,
            timing_ms=1,
        )

    return navigate


def _fake_extract(prompt: BenchmarkPrompt):
    async def extract(settings: Settings, **kwargs: Any) -> ExtractionResult:
        del settings
        text = _evidence_text(prompt, prompt.expected_sources[0] if prompt.expected_sources else prompt.id)
        return ExtractionResult(
            selector=str(kwargs["selector"]),
            extraction_goal=str(kwargs["extraction_goal"]),
            records=[{"text": text, "index": 0}],
            text_excerpt=text,
            record_count=1,
            schema_valid=True,
        )

    return extract


def _source_url(expected_source: str, prompt_id: str) -> str:
    source = expected_source.strip().removeprefix("https://").removeprefix("http://").rstrip("/")
    return f"https://{source}/ghostresearcher-eval/{prompt_id}"


def _evidence_text(prompt: BenchmarkPrompt, source: str) -> str:
    must_include = "; ".join(_string_list(prompt.eval_criteria, "must_include"))
    freshness = "latest recent 2026" if bool(prompt.eval_criteria.get("freshness_required")) else "stable reference"
    return f"Evidence for {prompt.prompt}. Source {source}. Includes {must_include}. {freshness}."


def _source_trace_score(result: PlannerSequenceResult) -> float:
    if result.synthesis is None:
        return 0.0
    try:
        validate_report_sources(result.synthesis, result.session.evidence_records)
    except ReportValidationError:
        return 0.0
    return 1.0


def _criteria_coverage(prompt: BenchmarkPrompt, report_text: str) -> float:
    must_include = _string_list(prompt.eval_criteria, "must_include")
    if not must_include:
        return 1.0
    lowered = report_text.lower()
    matched = sum(1 for phrase in must_include if phrase.lower() in lowered)
    return _ratio(matched, len(must_include))


def _freshness_score(prompt: BenchmarkPrompt, report_text: str) -> float:
    if not bool(prompt.eval_criteria.get("freshness_required")):
        return 1.0
    lowered = report_text.lower()
    return 1.0 if any(marker in lowered for marker in ("2026", "latest", "recent", "today", "this week", "this month")) else 0.0


def _expected_source_matches(expected_sources: list[str], actual_sources: list[str]) -> list[str]:
    matches: list[str] = []
    for expected_source in expected_sources:
        normalized = expected_source.lower().removeprefix("https://").removeprefix("http://")
        if any(normalized in actual_source.lower() for actual_source in actual_sources):
            matches.append(expected_source)
    return matches


def _report_text(payload: dict[str, Any]) -> str:
    parts = [str(payload.get("title", "")), str(payload.get("summary", ""))]
    for finding in payload.get("key_findings", []):
        if isinstance(finding, dict):
            parts.append(str(finding.get("text", "")))
    return "\n".join(parts)


def _limitations(prompt: BenchmarkPrompt, metrics: dict[str, Any]) -> list[str]:
    limitations: list[str] = []
    if metrics["source_count"] < prompt.min_sources:
        limitations.append("source_count_below_benchmark_minimum")
    if metrics["expected_source_score"] < 1.0:
        limitations.append("expected_source_coverage_incomplete")
    if metrics["criteria_coverage_score"] < 1.0:
        limitations.append("criteria_terms_missing_from_report")
    return limitations


def _ratio(numerator: int | float, denominator: int | float) -> float:
    if denominator <= 0:
        return 1.0
    return round(max(0.0, min(1.0, float(numerator) / float(denominator))), 3)


def _required_string(payload: dict[str, Any], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"invalid_{key}")
    return value.strip()


def _string_list(payload: dict[str, Any], key: str) -> list[str]:
    value = payload.get(key, [])
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run GhostResearcher benchmark evals.")
    parser.add_argument("--benchmark", type=Path, default=DEFAULT_BENCHMARK_PATH)
    parser.add_argument("--results-dir", type=Path, default=DEFAULT_RESULTS_DIR)
    parser.add_argument("--mode", choices=["offline", "live"], default="offline")
    parser.add_argument("--limit", type=int, default=3, help="Number of benchmark prompts to run. Use 0 for all prompts.")
    parser.add_argument("--no-write", action="store_true", help="Print results without writing an artifact.")
    return parser.parse_args()


async def _main() -> None:
    args = _parse_args()
    prompts = load_benchmark_prompts(args.benchmark)
    selected_prompts = prompts if args.limit == 0 else prompts[: args.limit]
    payload = await run_eval_suite(prompts=selected_prompts, mode=args.mode)
    if not args.no_write:
        path = write_eval_results(payload, results_dir=args.results_dir)
        payload["artifact_path"] = str(path)
    print(json.dumps(payload, indent=2, sort_keys=True))


if __name__ == "__main__":
    asyncio.run(_main())
