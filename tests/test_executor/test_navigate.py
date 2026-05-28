"""Regression tests for the navigate_to_url executor action."""

from __future__ import annotations

import unittest
from contextlib import asynccontextmanager

from backend.config import Settings
from backend.executor.navigate import navigate_to_url


class FakeResponse:
    def __init__(self, status: int) -> None:
        self.status = status


class FakePage:
    def __init__(self, *, url: str, title: str, content: str, links: list[str], status_code: int = 200) -> None:
        self.url = url
        self._final_url = url
        self._title = title
        self._content = content
        self._links = links
        self._status_code = status_code
        self.waited_for: str | None = None

    async def goto(self, url: str, *, wait_until: str, timeout: float) -> FakeResponse:
        self.url = self._final_url
        return FakeResponse(self._status_code)

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
        self.assertFalse(result.detection_blocked)
        self.assertEqual("#content", fake_page.waited_for)

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

    async def test_navigate_rejects_invalid_urls(self) -> None:
        with self.assertRaisesRegex(ValueError, "invalid_url"):
            await navigate_to_url(Settings.from_env({}), url="ftp://example.com")


if __name__ == "__main__":
    unittest.main()
