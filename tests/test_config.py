"""Regression tests for GhostResearcher runtime settings."""

from __future__ import annotations

import unittest

from backend.config import Settings


class SettingsTests(unittest.TestCase):
    def test_defaults_match_env_template(self) -> None:
        settings = Settings.from_env({})

        self.assertEqual("http://localhost:9222", settings.cloak_cdp_url)
        self.assertEqual("https://openrouter.ai/api/v1", settings.openrouter_base_url)
        self.assertEqual("GhostResearcher", settings.openrouter_app_title)
        self.assertEqual("deepseek/deepseek-v4-flash", settings.default_planner_model)
        self.assertEqual("deepseek/deepseek-v4-pro", settings.fallback_planner_model)
        self.assertEqual(20, settings.max_steps_per_job)
        self.assertEqual(50000, settings.max_tokens_per_job)
        self.assertEqual(0.05, settings.max_model_cost_per_job_usd)
        self.assertEqual(0.02, settings.warn_model_cost_per_job_usd)
        self.assertTrue(settings.scrape_enabled)
        self.assertEqual("INFO", settings.log_level)
        self.assertEqual(["http://localhost:3000", "http://127.0.0.1:3000"], settings.cors_allowed_origins)

    def test_boolean_and_numeric_overrides_parse(self) -> None:
        settings = Settings.from_env(
            {
                "MAX_STEPS_PER_JOB": "12",
                "MAX_TOKENS_PER_JOB": "12000",
                "MAX_MODEL_COST_PER_JOB_USD": "0.03",
                "WARN_MODEL_COST_PER_JOB_USD": "0.01",
                "DEFAULT_PLANNER_MODEL": "qwen/test-model",
                "SCRAPE_ENABLED": "false",
                "LOG_LEVEL": "DEBUG",
                "CORS_ALLOWED_ORIGINS": "https://ghost.example, http://localhost:3000",
            }
        )

        self.assertEqual(12, settings.max_steps_per_job)
        self.assertEqual(12000, settings.max_tokens_per_job)
        self.assertEqual(0.03, settings.max_model_cost_per_job_usd)
        self.assertEqual(0.01, settings.warn_model_cost_per_job_usd)
        self.assertEqual("qwen/test-model", settings.default_planner_model)
        self.assertFalse(settings.scrape_enabled)
        self.assertEqual("DEBUG", settings.log_level)
        self.assertEqual(["https://ghost.example", "http://localhost:3000"], settings.cors_allowed_origins)


if __name__ == "__main__":
    unittest.main()
