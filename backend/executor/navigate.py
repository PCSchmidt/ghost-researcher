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
    timeout_seconds: float = 10.0,
    page_context_factory: PageContextFactory | None = None,
) -> NavigationResult:
    """Navigate to a URL via CloakBrowser and return normalized page state."""
    del fingerprint_seed
    _validate_url(url)
    page_context = page_context_factory or _default_page_context
    timeout_ms = timeout_seconds * 1000
    started_at = perf_counter()

    async with page_context(settings) as page:
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

    detection_blocked, blocked_reason = _detect_block(title, content)
    timing_ms = int((perf_counter() - started_at) * 1000)
    return NavigationResult(
        url=url,
        final_url=page.url,
        title=title,
        status_code=response.status if response is not None else 200,
        content_excerpt=_extract_excerpt(content),
        links=links,
        detection_blocked=detection_blocked,
        blocked_reason=blocked_reason,
        screenshot_path=None,
        timing_ms=timing_ms,
    )
