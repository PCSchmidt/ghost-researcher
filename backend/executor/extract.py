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
    async def evaluate(self, expression: str, *args: Any) -> Any: ...


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


def _is_browser_noise(value: str) -> bool:
    return any(marker in value for marker in ("won't see your activity", "Chrome", "third-party cookies"))


def _strip_browser_noise(value: str) -> str:
    clean = value
    for prefix in ("You've gone Incognito", "You\u2019ve gone Incognito"):
        if prefix in clean:
            clean = clean.split(prefix, 1)[-1].strip()
    return clean


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
        # Reuse the most recent page left open by navigate_to_url.
        page = context.pages[-1] if context.pages else await context.new_page()
        # Wait for any in-flight navigation to settle.
        try:
            await page.wait_for_load_state("domcontentloaded", timeout=5000)
        except Exception:
            pass
        yield page
    finally:
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
        # Wait a moment for JS-rendered content to populate.
        await page.wait_for_timeout(1500)

        selector_candidates = []
        for candidate in (_selector, "article", "main", "[role='main']", ".content", "#content", "body"):
            if candidate not in selector_candidates:
                selector_candidates.append(candidate)

        raw_sections = await page.evaluate(
            """
            (selectors) => {
              const sections = [];
              for (const selector of selectors) {
                const nodes = Array.from(document.querySelectorAll(selector));
                for (const node of nodes) {
                  const text = (node.innerText || node.textContent || '').trim();
                  if (text) sections.push({ selector, text });
                }
              }
              return sections;
            }
            """,
            selector_candidates,
        )
        if isinstance(raw_sections, list):
            records = []
            seen_text: set[str] = set()
            for index, section in enumerate(raw_sections):
                if not isinstance(section, dict):
                    continue
                text = section.get("text")
                if not isinstance(text, str):
                    continue
                clean = _normalize_text(_strip_browser_noise(text))
                if not clean or _is_browser_noise(clean) or clean in seen_text:
                    continue
                seen_text.add(clean)
                records.append(
                    {
                        "text": clean,
                        "index": index,
                        "selector": str(section.get("selector") or _selector),
                    }
                )
        else:
            # Older fakes and some browser shims return a plain body string.
            clean = _normalize_text(_strip_browser_noise(str(raw_sections or "")))
            records = [{"text": clean, "index": 0, "selector": _selector}] if clean else []

        # If innerText returned only Chrome UI noise (Incognito banner, privacy
        # interstitial), fall back to raw HTML text extraction.
        if not records:
            html = await page.content()
            # Strip HTML tags, scripts, styles
            import re as _re
            text = _re.sub(r"<script[^>]*>.*?</script>", "", html, flags=_re.DOTALL)
            text = _re.sub(r"<style[^>]*>.*?</style>", "", text, flags=_re.DOTALL)
            text = _re.sub(r"<[^>]+>", " ", text)
            text = _re.sub(r"\s+", " ", text).strip()
            # Strip Chrome incognito banner from HTML source too
            for prefix in ("You've gone Incognito", "You\u2019ve gone Incognito"):
                if prefix in text:
                    text = text.split(prefix, 1)[-1].strip()
            if text and len(text) > 100:
                records = [{"text": _normalize_text(text), "index": 0, "selector": "html"}]
    text_excerpt = " ".join(record["text"] for record in records)[:2000]
    schema_valid = all(_validate_record_against_schema(record, output_schema) for record in records)
    return ExtractionResult(
        selector=selector,
        extraction_goal=extraction_goal,
        records=records,
        text_excerpt=text_excerpt,
        record_count=len(records),
        schema_valid=schema_valid,
    )
