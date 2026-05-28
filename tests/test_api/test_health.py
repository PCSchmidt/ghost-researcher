"""Regression tests for the backend health route."""

from __future__ import annotations

import unittest

from fastapi.testclient import TestClient

from backend.main import create_app
from backend.executor.browser import BrowserHealth


class HealthRouteTests(unittest.TestCase):
    def test_health_reports_liveness_and_missing_dependencies(self) -> None:
        client = TestClient(
            create_app(
                {},
                browser_health_resolver=lambda: BrowserHealth(
                    status="ok",
                    version_url="http://localhost:9222/json/version",
                    browser="CloakBrowser/1.0",
                ),
            )
        )

        response = client.get("/health")

        self.assertEqual(200, response.status_code)
        payload = response.json()
        self.assertEqual("ok", payload["status"])
        self.assertEqual("ghostresearcher-api", payload["service"])
        self.assertEqual("ok", payload["dependencies"]["cloak_cdp"]["status"])
        self.assertEqual("missing", payload["dependencies"]["redis"])
        self.assertEqual(20, payload["limits"]["max_steps_per_job"])

    def test_health_reports_configured_services_and_disabled_scraping(self) -> None:
        client = TestClient(
            create_app(
                {
                    "DATABASE_URL": "postgresql://example",
                    "REDIS_URL": "redis://example",
                    "ANTHROPIC_API_KEY": "test-key",
                    "SCRAPE_ENABLED": "false",
                    "MAX_STEPS_PER_JOB": "8",
                },
                browser_health_resolver=lambda: BrowserHealth(
                    status="disabled",
                    version_url="http://localhost:9222/json/version",
                    detail="scraping disabled",
                ),
            )
        )

        response = client.get("/health")

        self.assertEqual(200, response.status_code)
        payload = response.json()
        self.assertEqual("configured", payload["dependencies"]["anthropic"])
        self.assertEqual("configured", payload["dependencies"]["database"])
        self.assertEqual("configured", payload["dependencies"]["redis"])
        self.assertEqual("disabled", payload["dependencies"]["cloak_cdp"]["status"])
        self.assertEqual(8, payload["limits"]["max_steps_per_job"])


if __name__ == "__main__":
    unittest.main()
