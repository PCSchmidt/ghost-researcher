"""Regression tests for the navigate_to_url executor action."""

from __future__ import annotations

import unittest
from contextlib import asynccontextmanager

from backend.config import Settings
from backend.executor.navigate import navigate_to_url


class FakeResponse:
    def __init__(self, status: int, headers: dict[str, str] | None = None) -> None:
        self.status = status
        self.headers = headers or {}


class FakePage:
    def __init__(
        self,
        *,
        url: str,
        title: str,
        content: str,
        links: list[str],
        status_code: int = 200,
        headers: dict[str, str] | None = None,
    ) -> None:
        self.url = url
        self._final_url = url
        self._title = title
        self._content = content
        self._links = links
        self._status_code = status_code
        self._headers = headers or {}
        self.waited_for: str | None = None

    async def goto(self, url: str, *, wait_until: str, timeout: float) -> FakeResponse:
        self.url = self._final_url
        return FakeResponse(self._status_code, self._headers)

    async def wait_for_selector(self, selector: str, *, timeout: float) -> None:
        self.waited_for = selector

    async def title(self) -> str:
        return self._title

    async def content(self) -> str:
        return self._content

    async def eval_on_selector_all(self, selector: str, expression: str) -> list[str]:
        return self._links


class NavigateTests(unittest.IsolatedAsyncioTestCase):
    async def test_navigate_returns_normalized_page_state(self) -> None:
        fake_page = FakePage(
            url="https://example.com/final",
            title="Example Domain",
            content="<html><body>Hello world from GhostResearcher</body></html>",
            links=["https://example.com/about"],
            status_code=201,
        )

        @asynccontextmanager
        async def fake_context(settings: Settings):
            yield fake_page

        result = await navigate_to_url(
            Settings.from_env({}),
            url="https://example.com/start",
            wait_for="#content",
            page_context_factory=fake_context,
        )

        self.assertEqual("https://example.com/start", result.url)
        self.assertEqual("https://example.com/final", result.final_url)
        self.assertEqual("Example Domain", result.title)
        self.assertEqual(201, result.status_code)
        self.assertEqual(["https://example.com/about"], result.links)
        self.assertEqual("html", result.page_type)
        self.assertFalse(result.detection_blocked)
        self.assertEqual("#content", fake_page.waited_for)

    async def test_navigation_timeout_is_caught_not_raised(self) -> None:
        # A slow/stuck page (goto timeout) must not propagate and 500 the whole
        # research run; it should come back as a blocked, skippable source.
        class TimeoutPage:
            url = "https://slow.example/start"

            async def goto(self, url: str, *, wait_until: str, timeout: float) -> None:
                raise TimeoutError("Timeout 20000ms exceeded")

            async def wait_for_selector(self, selector: str, *, timeout: float) -> None:
                return None

            async def title(self) -> str:
                return ""

            async def content(self) -> str:
                return ""

            async def eval_on_selector_all(self, selector: str, expression: str) -> list[str]:
                return []

        @asynccontextmanager
        async def fake_context(settings: Settings):
            yield TimeoutPage()

        result = await navigate_to_url(
            Settings.from_env({}),
            url="https://slow.example/start",
            page_context_factory=fake_context,
        )

        self.assertTrue(result.detection_blocked)
        self.assertEqual("blocked", result.page_type)
        self.assertEqual(0, result.status_code)
        self.assertTrue(result.blocked_reason.startswith("navigation_error:"))

    async def test_hung_navigation_is_bounded_by_overall_timeout(self) -> None:
        # A degraded shared browser can hang a page operation indefinitely (no
        # exception). The overall navigate backstop must cancel it and return a
        # blocked source so the planner moves on instead of the job hanging.
        import asyncio

        class HangingPage:
            url = "https://hang.example/start"

            async def goto(self, url: str, *, wait_until: str, timeout: float) -> None:
                await asyncio.sleep(60)  # never returns within the test budget

            async def wait_for_selector(self, selector: str, *, timeout: float) -> None:
                return None

            async def title(self) -> str:
                return ""

            async def content(self) -> str:
                return ""

            async def eval_on_selector_all(self, selector: str, expression: str) -> list[str]:
                return []

        @asynccontextmanager
        async def fake_context(settings: Settings):
            yield HangingPage()

        # timeout_seconds=0.05 -> overall backstop ~0.15s, so this resolves fast.
        result = await navigate_to_url(
            Settings.from_env({}),
            url="https://hang.example/start",
            timeout_seconds=0.05,
            page_context_factory=fake_context,
        )

        self.assertTrue(result.detection_blocked)
        self.assertEqual("blocked", result.page_type)
        self.assertEqual("navigation_timeout", result.blocked_reason)

    async def test_navigate_detects_bot_challenge_content(self) -> None:
        fake_page = FakePage(
            url="https://example.com/challenge",
            title="Security Check",
            content="<html><body>Please verify you are human before continuing.</body></html>",
            links=[],
        )

        @asynccontextmanager
        async def fake_context(settings: Settings):
            yield fake_page

        result = await navigate_to_url(
            Settings.from_env({}),
            url="https://example.com/challenge",
            page_context_factory=fake_context,
        )

        self.assertTrue(result.detection_blocked)
        self.assertEqual("bot_challenge", result.blocked_reason)
        self.assertEqual("blocked", result.page_type)

    async def test_navigate_classifies_pdf_content(self) -> None:
        fake_page = FakePage(
            url="https://example.com/report.pdf",
            title="PDF Report",
            content="<html><body>PDF viewer</body></html>",
            links=[],
            headers={"content-type": "application/pdf"},
        )

        @asynccontextmanager
        async def fake_context(settings: Settings):
            yield fake_page

        result = await navigate_to_url(
            Settings.from_env({}),
            url="https://example.com/report.pdf",
            page_context_factory=fake_context,
        )

        self.assertEqual("application/pdf", result.content_type)
        self.assertEqual("pdf", result.page_type)

    async def test_navigate_classifies_paywall_and_thin_spa_pages(self) -> None:
        paywall_page = FakePage(
            url="https://example.com/paywall",
            title="Members only",
            content="<html><body>Please subscribe to continue reading.</body></html>",
            links=[],
        )
        spa_page = FakePage(
            url="https://example.com/app",
            title="App",
            content="<html><body><div id='root'></div><script src='/app.js'></script></body></html>",
            links=[],
        )

        @asynccontextmanager
        async def paywall_context(settings: Settings):
            yield paywall_page

        @asynccontextmanager
        async def spa_context(settings: Settings):
            yield spa_page

        paywall_result = await navigate_to_url(
            Settings.from_env({}),
            url="https://example.com/paywall",
            page_context_factory=paywall_context,
        )
        spa_result = await navigate_to_url(
            Settings.from_env({}),
            url="https://example.com/app",
            page_context_factory=spa_context,
        )

        self.assertEqual("paywall", paywall_result.page_type)
        self.assertEqual("spa_thin", spa_result.page_type)

    async def test_navigate_rejects_invalid_urls(self) -> None:
        with self.assertRaisesRegex(ValueError, "invalid_url"):
            await navigate_to_url(Settings.from_env({}), url="ftp://example.com")


if __name__ == "__main__":
    unittest.main()
