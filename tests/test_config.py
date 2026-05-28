"""Regression tests for GhostResearcher runtime settings."""

from __future__ import annotations

import unittest

from backend.config import Settings


class SettingsTests(unittest.TestCase):
    def test_defaults_match_env_template(self) -> None:
        settings = Settings.from_env({})

        self.assertEqual("http://localhost:9222", settings.cloak_cdp_url)
        self.assertEqual(20, settings.max_steps_per_job)
        self.assertEqual(50000, settings.max_tokens_per_job)
        self.assertTrue(settings.scrape_enabled)
        self.assertEqual("INFO", settings.log_level)

    def test_boolean_and_numeric_overrides_parse(self) -> None:
        settings = Settings.from_env(
            {
                "MAX_STEPS_PER_JOB": "12",
                "MAX_TOKENS_PER_JOB": "12000",
                "SCRAPE_ENABLED": "false",
                "LOG_LEVEL": "DEBUG",
            }
        )

        self.assertEqual(12, settings.max_steps_per_job)
        self.assertEqual(12000, settings.max_tokens_per_job)
        self.assertFalse(settings.scrape_enabled)
        self.assertEqual("DEBUG", settings.log_level)


if __name__ == "__main__":
    unittest.main()
