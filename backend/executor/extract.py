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


def _record_text(record: dict[str, Any]) -> str:
    value = record.get("text")
    return value if isinstance(value, str) else ""


def _metadata_record(metadata: dict[str, Any]) -> dict[str, Any] | None:
    parts = [
        str(metadata.get("title") or "").strip(),
        str(metadata.get("description") or "").strip(),
        str(metadata.get("published_time") or "").strip(),
        str(metadata.get("canonical_url") or "").strip(),
    ]
    text = _normalize_text(". ".join(part for part in parts if part))
    if not text:
        return None
    return {
        "text": text,
        "index": -1,
        "selector": "metadata",
        "record_type": "metadata",
        "title": str(metadata.get("title") or ""),
        "description": str(metadata.get("description") or ""),
        "published_time": str(metadata.get("published_time") or ""),
        "canonical_url": str(metadata.get("canonical_url") or ""),
    }


def _limitation_record(metadata: dict[str, Any], page_text: str) -> dict[str, Any] | None:
    page_type = str(metadata.get("page_type") or "html")
    if page_type not in {"pdf", "paywall", "spa_thin"}:
        return None
    title = str(metadata.get("title") or "Untitled source")
    url = str(metadata.get("document_url") or metadata.get("canonical_url") or "")
    if page_type == "pdf":
        detail = "PDF source detected; browser text extraction is limited without a PDF text parser."
    elif page_type == "paywall":
        detail = "Paywall or sign-in gate detected; extracted text may reflect access limitations."
    else:
        detail = "Thin JavaScript application shell detected; page may need longer rendering or API-backed extraction."
    text = _normalize_text(f"{detail} Title: {title}. URL: {url}. Visible text: {page_text[:500]}")
    return {
        "text": text,
        "index": -2,
        "selector": page_type,
        "record_type": "limitation",
        "page_type": page_type,
    }


def _page_type_from_metadata(metadata: dict[str, Any], page_text: str) -> str:
    content_type = str(metadata.get("content_type") or "").lower()
    document_url = str(metadata.get("document_url") or "").lower()
    if "application/pdf" in content_type or document_url.endswith(".pdf"):
        return "pdf"
    if re.search(r"subscribe|sign in to continue|create an account|paywall|members only", page_text, re.IGNORECASE):
        return "paywall"
    if len(page_text) < 120 and bool(metadata.get("has_app_shell")):
        return "spa_thin"
    return "html"


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

        extraction_payload = await page.evaluate(
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
              const byName = (name) => document.querySelector(`meta[name="${name}"]`)?.content || '';
              const byProp = (name) => document.querySelector(`meta[property="${name}"]`)?.content || '';
              const bodyText = (document.body?.innerText || document.body?.textContent || '').trim();
              return {
                sections,
                metadata: {
                  title: document.title || byProp('og:title'),
                  description: byName('description') || byProp('og:description'),
                  published_time: byProp('article:published_time') || byName('date') || byName('pubdate'),
                  canonical_url: document.querySelector('link[rel="canonical"]')?.href || '',
                  document_url: document.location?.href || '',
                  content_type: document.contentType || '',
                  has_app_shell: Boolean(document.querySelector('#root, #app, [data-reactroot], [id="__next"]')),
                  body_text: bodyText,
                },
              };
            }
            """,
            selector_candidates,
        )
        metadata: dict[str, Any] = {}
        raw_sections = extraction_payload
        if isinstance(extraction_payload, dict):
            raw_sections = extraction_payload.get("sections", [])
            raw_metadata = extraction_payload.get("metadata", {})
            if isinstance(raw_metadata, dict):
                metadata = raw_metadata
                page_text = _normalize_text(str(metadata.get("body_text") or ""))
                metadata["page_type"] = _page_type_from_metadata(metadata, page_text)
        if isinstance(raw_sections, list):
            records = []
            seen_text: set[str] = set()
            metadata_record = _metadata_record(metadata)
            if metadata_record is not None:
                records.append(metadata_record)
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
                        "record_type": "content",
                    }
                )
            page_text = _normalize_text(str(metadata.get("body_text") or " ".join(_record_text(record) for record in records)))
            limitation_record = _limitation_record(metadata, page_text)
            if limitation_record is not None:
                records.append(limitation_record)
        else:
            # Older fakes and some browser shims return a plain body string.
            clean = _normalize_text(_strip_browser_noise(str(raw_sections or "")))
            records = [{"text": clean, "index": 0, "selector": _selector, "record_type": "content"}] if clean else []

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
                records = [{"text": _normalize_text(text), "index": 0, "selector": "html", "record_type": "html_fallback"}]
    text_excerpt = " ".join(_record_text(record) for record in records)[:2000]
    schema_valid = all(_validate_record_against_schema(record, output_schema) for record in records)
    return ExtractionResult(
        selector=selector,
        extraction_goal=extraction_goal,
        records=records,
        text_excerpt=text_excerpt,
        record_count=len(records),
        schema_valid=schema_valid,
    )
