"""Regression tests for FastAPI app wiring."""

from __future__ import annotations

import unittest

from fastapi.testclient import TestClient

from backend.main import create_app


class AppCorsTests(unittest.TestCase):
    def test_vercel_preview_origin_is_allowed(self) -> None:
        app = create_app(
            {
                "CORS_ALLOWED_ORIGINS": "https://ghost-researcher.vercel.app",
            }
        )

        with TestClient(app) as client:
            response = client.options(
                "/research",
                headers={
                    "Origin": "https://ghost-researcher-o8jwxsj7a-chris-schmidts-projects.vercel.app",
                    "Access-Control-Request-Method": "POST",
                    "Access-Control-Request-Headers": "content-type",
                },
            )

        self.assertEqual(200, response.status_code)
        self.assertEqual(
            "https://ghost-researcher-o8jwxsj7a-chris-schmidts-projects.vercel.app",
            response.headers.get("access-control-allow-origin"),
        )


if __name__ == "__main__":
    unittest.main()
