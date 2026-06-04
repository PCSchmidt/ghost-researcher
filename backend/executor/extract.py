"""Structured extraction skeleton for the current browser page."""

from __future__ import annotations

import re
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Any, AsyncIterator, Protocol

from playwright.async_api import Browser, Page, Playwright, async_playwright

from backend.config import Settings
from backend.executor.browser import async_resolve_cdp_ws_endpoint


class PageLike(Protocol):
    async def eval_on_selector_all(self, selector: str, expression: str) -> list[str]: ...


PageContextFactory = Any


@dataclass(frozen=True, slots=True)
class ExtractionResult:
    """Normalized output for extract_structured_data."""

    selector: str
    extraction_goal: str
    records: list[dict[str, Any]]
    text_excerpt: str
    record_count: int
    schema_valid: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "selector": self.selector,
            "extraction_goal": self.extraction_goal,
            "records": self.records,
            "text_excerpt": self.text_excerpt,
            "record_count": self.record_count,
            "schema_valid": self.schema_valid,
        }


def _normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def _validate_record_against_schema(record: dict[str, Any], output_schema: dict[str, Any] | None) -> bool:
    if output_schema is None:
        return True
    required = output_schema.get("required", [])
    if not isinstance(required, list):
        return False
    return all(field in record for field in required)


@asynccontextmanager
async def _default_page_context(settings: Settings) -> AsyncIterator[Page]:
    playwright: Playwright | None = None
    browser: Browser | None = None
    page: Page | None = None
    try:
        playwright = await async_playwright().start()
        ws_endpoint = await async_resolve_cdp_ws_endpoint(settings)
        browser = await playwright.chromium.connect_over_cdp(ws_endpoint)
        context = browser.contexts[0] if browser.contexts else await browser.new_context()
        page = context.pages[-1] if context.pages else await context.new_page()
        yield page
    finally:
        if page is not None:
            await page.close()
        if browser is not None:
            await browser.close()
        if playwright is not None:
            await playwright.stop()


async def extract_structured_data(
    settings: Settings,
    *,
    selector: str = "body",
    extraction_goal: str,
    output_schema: dict[str, Any] | None = None,
    page_context_factory: PageContextFactory | None = None,
) -> ExtractionResult:
    """Extract text records from the current page using a selector."""
    _selector = selector.strip() if selector else "body"
    page_context = page_context_factory or _default_page_context
    async with page_context(settings) as page:
        raw_values = await page.eval_on_selector_all(
            _selector,
            "elements => elements.map((element) => element.innerText || element.textContent || '').filter(Boolean)",
        )

    records = [
        {"text": _normalize_text(value), "index": index}
        for index, value in enumerate(raw_values)
        if _normalize_text(value)
    ]
    # Fallback: if body extraction returns nothing (SPA / JS-rendered pages),
    # grab the full <body> innerText via page.evaluate.
    if not records and _selector == "body":
        async with page_context(settings) as page:
            fallback_text = await page.evaluate("document.body.innerText")
        if fallback_text and isinstance(fallback_text, str):
            records = [{"text": _normalize_text(fallback_text), "index": 0}]
    text_excerpt = " ".join(record["text"] for record in records)[:500]
    schema_valid = all(_validate_record_against_schema(record, output_schema) for record in records)
    return ExtractionResult(
        selector=selector,
        extraction_goal=extraction_goal,
        records=records,
        text_excerpt=text_excerpt,
        record_count=len(records),
        schema_valid=schema_valid,
    )
