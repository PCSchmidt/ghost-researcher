"""Regression tests for the CloakBrowser health client."""

from __future__ import annotations

import unittest
from urllib.error import URLError

from backend.config import Settings
from backend.executor.browser import CloakBrowserClient


class CloakBrowserClientTests(unittest.TestCase):
    def test_version_url_uses_json_version_endpoint(self) -> None:
        client = CloakBrowserClient(Settings.from_env({"CLOAK_CDP_URL": "http://localhost:9222"}))

        self.assertEqual("http://localhost:9222/json/version", client.version_url)

    def test_version_url_normalizes_websocket_scheme(self) -> None:
        client = CloakBrowserClient(Settings.from_env({"CLOAK_CDP_URL": "ws://localhost:9222/devtools/browser/123"}))

        self.assertEqual(
            "http://localhost:9222/devtools/browser/123/json/version",
            client.version_url,
        )

    def test_healthcheck_returns_ok_when_payload_is_valid(self) -> None:
        def fake_fetch(url: str, timeout: float) -> str:
            self.assertEqual("http://localhost:9222/json/version", url)
            self.assertEqual(2.0, timeout)
            return '{"Browser": "CloakBrowser/1.0", "webSocketDebuggerUrl": "ws://localhost:9222/devtools/browser/abc"}'

        client = CloakBrowserClient(Settings.from_env({}), fetch_text=fake_fetch)

        health = client.healthcheck()

        self.assertEqual("ok", health.status)
        self.assertEqual("CloakBrowser/1.0", health.browser)
        self.assertEqual("ws://localhost:9222/devtools/browser/abc", health.websocket_debugger_url)

    def test_healthcheck_handles_disabled_scraping(self) -> None:
        client = CloakBrowserClient(Settings.from_env({"SCRAPE_ENABLED": "false"}))

        health = client.healthcheck()

        self.assertEqual("disabled", health.status)
        self.assertEqual("scraping disabled", health.detail)

    def test_healthcheck_handles_unreachable_endpoint(self) -> None:
        def fake_fetch(url: str, timeout: float) -> str:
            raise URLError("connection refused")

        client = CloakBrowserClient(Settings.from_env({}), fetch_text=fake_fetch)

        health = client.healthcheck()

        self.assertEqual("unreachable", health.status)
        self.assertIn("connection refused", health.detail)


if __name__ == "__main__":
    unittest.main()
