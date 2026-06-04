"""Regression tests for the CloakBrowser health client."""

from __future__ import annotations

import unittest
from typing import Any
from urllib.error import URLError

from backend.config import Settings
from backend.executor.browser import CloakBrowserClient, resolve_cdp_ws_endpoint


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

    def test_resolve_cdp_ws_endpoint_rewrites_host_to_configured_netloc(self) -> None:
        def fake_fetch(url: str, timeout: float) -> str:
            self.assertEqual("http://cloak.internal:9222/json/version", url)
            return '{"webSocketDebuggerUrl": "ws://127.0.0.1:9223/devtools/browser/abc-123"}'

        settings = Settings.from_env({"CLOAK_CDP_URL": "http://cloak.internal:9222"})
        ws_url = resolve_cdp_ws_endpoint(settings, fetch_text=fake_fetch)

        # Should match internal host:port but keep the UUID path from the fetched URL
        self.assertEqual("ws://cloak.internal:9222/devtools/browser/abc-123", ws_url)

    def test_resolve_cdp_ws_endpoint_raises_on_missing_debugger_url(self) -> None:
        def fake_fetch(url: str, timeout: float) -> str:
            return '{"Browser": "Chrome/123.0"}'  # Missing webSocketDebuggerUrl

        settings = Settings.from_env({"CLOAK_CDP_URL": "http://localhost:9222"})
        with self.assertRaisesRegex(RuntimeError, "missing_websocket_debugger_url"):
            resolve_cdp_ws_endpoint(settings, fetch_text=fake_fetch)


if __name__ == "__main__":
    unittest.main()
