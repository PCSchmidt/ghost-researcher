"""First concrete executor action for page navigation."""

from __future__ import annotations

import re
from contextlib import asynccontextmanager
from dataclasses import dataclass
from time import perf_counter
from typing import Any, AsyncIterator, Protocol
from urllib.parse import urlparse

from playwright.async_api import Browser, Page, Playwright, async_playwright

from backend.config import Settings
from backend.executor.browser import async_resolve_cdp_ws_endpoint


class ResponseLike(Protocol):
    status: int
    headers: dict[str, str]


class PageLike(Protocol):
    url: str

    async def goto(self, url: str, *, wait_until: str, timeout: float) -> ResponseLike | None: ...

    async def wait_for_selector(self, selector: str, *, timeout: float) -> None: ...

    async def title(self) -> str: ...

    async def content(self) -> str: ...

    async def eval_on_selector_all(self, selector: str, expression: str) -> list[str]: ...


PageContextFactory = Any

DETECTION_PATTERNS = {
    "captcha": re.compile(r"captcha", re.IGNORECASE),
    "access_denied": re.compile(r"access denied|forbidden", re.IGNORECASE),
    "bot_challenge": re.compile(r"verify you are human|bot detection|security check", re.IGNORECASE),
}

PAYWALL_PATTERN = re.compile(r"subscribe|sign in to continue|create an account|paywall|members only", re.IGNORECASE)


@dataclass(frozen=True, slots=True)
class NavigationResult:
    """Normalized result returned by navigate_to_url."""

    url: str
    final_url: str
    title: str
    status_code: int
    content_excerpt: str
    links: list[str]
    detection_blocked: bool
    blocked_reason: str | None
    screenshot_path: str | None
    timing_ms: int
    content_type: str | None = None
    page_type: str = "html"

    def to_dict(self) -> dict[str, Any]:
        return {
            "url": self.url,
            "final_url": self.final_url,
            "title": self.title,
            "status_code": self.status_code,
            "content_excerpt": self.content_excerpt,
            "links": self.links,
            "detection_blocked": self.detection_blocked,
            "blocked_reason": self.blocked_reason,
            "screenshot_path": self.screenshot_path,
            "timing_ms": self.timing_ms,
            "content_type": self.content_type,
            "page_type": self.page_type,
        }


def _validate_url(url: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError(f"invalid_url:{url}")


def _extract_excerpt(content: str, *, max_length: int = 280) -> str:
    text = re.sub(r"<[^>]+>", " ", content)
    text = re.sub(r"\s+", " ", text).strip()
    return text[:max_length]


def _detect_block(title: str, content: str) -> tuple[bool, str | None]:
    haystack = f"{title}\n{content}"
    for reason, pattern in DETECTION_PATTERNS.items():
        if pattern.search(haystack):
            return True, reason
    return False, None


def _classify_page_type(
    *,
    final_url: str,
    content_type: str | None,
    title: str,
    content: str,
    excerpt: str,
    detection_blocked: bool,
) -> str:
    if detection_blocked:
        return "blocked"
    normalized_content_type = (content_type or "").lower()
    if "application/pdf" in normalized_content_type or urlparse(final_url).path.lower().endswith(".pdf"):
        return "pdf"
    if PAYWALL_PATTERN.search(f"{title}\n{content}"):
        return "paywall"
    if len(excerpt) < 120 and re.search(r"<script|__next|id=[\"']root[\"']|id=[\"']app[\"']", content, re.IGNORECASE):
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
        # Close pages left open by prior steps. The CloakBrowser CDP browser is
        # shared and long-lived; `browser.close()` here only disconnects, so pages
        # accumulate across navigate calls and eventually stall connect_over_cdp's
        # target sync (a single slow research job, or several jobs, can hang it).
        # Bounding the open-page count to one keeps reconnects fast.
        for existing_page in list(context.pages):
            try:
                await existing_page.close()
            except Exception:
                pass
        page = await context.new_page()
        yield page
    finally:
        # Don't close the page — extract needs it. Chromium keeps the page
        # alive in its context so the next Playwright connection sees it.
        if browser is not None:
            await browser.close()
        if playwright is not None:
            await playwright.stop()


async def navigate_to_url(
    settings: Settings,
    *,
    url: str,
    wait_for: str | None = None,
    fingerprint_seed: int | None = None,
    timeout_seconds: float = 20.0,
    page_context_factory: PageContextFactory | None = None,
) -> NavigationResult:
    """Navigate to a URL via CloakBrowser and return normalized page state."""
    del fingerprint_seed
    _validate_url(url)
    page_context = page_context_factory or _default_page_context
    timeout_ms = timeout_seconds * 1000
    started_at = perf_counter()

    async with page_context(settings) as page:
        try:
            response = await page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)
            # Model sometimes passes load-state keywords as wait_for; ignore them.
            _wait_for = wait_for.strip() if wait_for else ""
            if _wait_for and _wait_for.lower() not in (
                "domcontentloaded",
                "load",
                "networkidle",
                "networkidle0",
                "networkidle2",
            ):
                try:
                    await page.wait_for_selector(_wait_for, timeout=timeout_ms)
                except Exception:
                    pass  # selector may not exist on the target page; continue anyway
            title = await page.title()
            content = await page.content()
            links = await page.eval_on_selector_all(
                "a[href]",
                "elements => elements.map((element) => element.href).filter(Boolean).slice(0, 20)",
            )
            final_url = page.url
        except Exception as exc:
            # A slow, stuck, or unreachable page must not abort the whole research
            # run. Treat any navigation failure (goto timeout, network error) as a
            # skip-this-source signal so the planner moves on instead of the API
            # returning HTTP 500.
            return NavigationResult(
                url=url,
                final_url=url,
                title="",
                status_code=0,
                content_excerpt="",
                links=[],
                detection_blocked=True,
                blocked_reason=f"navigation_error:{type(exc).__name__}",
                screenshot_path=None,
                timing_ms=int((perf_counter() - started_at) * 1000),
                content_type=None,
                page_type="blocked",
            )

    detection_blocked, blocked_reason = _detect_block(title, content)
    timing_ms = int((perf_counter() - started_at) * 1000)
    content_type = None
    if response is not None:
        headers = getattr(response, "headers", {}) or {}
        content_type = headers.get("content-type") or headers.get("Content-Type")
    excerpt = _extract_excerpt(content)
    return NavigationResult(
        url=url,
        final_url=final_url,
        title=title,
        status_code=response.status if response is not None else 200,
        content_excerpt=excerpt,
        links=links,
        detection_blocked=detection_blocked,
        blocked_reason=blocked_reason,
        screenshot_path=None,
        timing_ms=timing_ms,
        content_type=content_type,
        page_type=_classify_page_type(
            final_url=page.url,
            content_type=content_type,
            title=title,
            content=content,
            excerpt=excerpt,
            detection_blocked=detection_blocked,
        ),
    )
