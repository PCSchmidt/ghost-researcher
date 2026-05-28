"""Regression tests for assess_credibility."""

from __future__ import annotations

import unittest

from backend.config import Settings
from backend.executor.credibility import assess_credibility


class AssessCredibilityTests(unittest.IsolatedAsyncioTestCase):
    async def test_gov_recent_source_scores_higher_than_generic_com(self) -> None:
        gov_result = await assess_credibility(
            Settings.from_env({}),
            url="https://faa.gov/newsroom/latest-uas-guidance",
            content_snippet="Latest FAA UAS guidance released in 2026.",
        )
        com_result = await assess_credibility(
            Settings.from_env({}),
            url="https://example.com/archive",
            content_snippet="Older overview of drone rules.",
        )

        self.assertGreater(gov_result.score, com_result.score)
        self.assertEqual(0.95, gov_result.domain_authority)
        self.assertIn("domain_authority", gov_result.rationale)

    async def test_empty_content_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "insufficient_content"):
            await assess_credibility(
                Settings.from_env({}),
                url="https://faa.gov/newsroom",
                content_snippet="   ",
            )


if __name__ == "__main__":
    unittest.main()
