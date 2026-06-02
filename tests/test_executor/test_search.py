"""Regression tests for web_search."""

from __future__ import annotations

import unittest

from backend.config import Settings
from backend.executor.search import BraveSearchProvider, SearchProviderError, web_search


class WebSearchTests(unittest.IsolatedAsyncioTestCase):
    async def test_search_returns_normalized_candidate_results(self) -> None:
        result = await web_search(
            Settings.from_env({}),
            query=" FAA BVLOS guidance ",
            num_results=3,
        )

        self.assertEqual("FAA BVLOS guidance", result.query)
        self.assertEqual(3, result.new_result_count)
        self.assertEqual(3, len(result.results))
        self.assertTrue(result.results[0].url.startswith("https://"))

    async def test_search_rejects_empty_query(self) -> None:
        with self.assertRaisesRegex(ValueError, "empty_query"):
            await web_search(Settings.from_env({}), query="   ")

    async def test_search_filters_existing_and_duplicate_urls(self) -> None:
        async def fake_provider(**kwargs: object) -> list[dict[str, str]]:
            return [
                {
                    "title": "Existing",
                    "url": "https://example.com/existing",
                    "snippet": "already seen",
                    "source_type": "web",
                },
                {
                    "title": "New",
                    "url": "https://example.com/new",
                    "snippet": "new source",
                    "source_type": "web",
                },
                {
                    "title": "Duplicate",
                    "url": "https://example.com/new",
                    "snippet": "duplicate source",
                    "source_type": "web",
                },
            ]

        result = await web_search(
            Settings.from_env({}),
            query="test query",
            existing_urls={"https://example.com/existing"},
            provider=fake_provider,
        )

        self.assertEqual(1, result.new_result_count)
        self.assertEqual("https://example.com/new", result.results[0].url)

    async def test_search_uses_configured_brave_provider(self) -> None:
        captured: dict[str, object] = {}

        def fake_fetch_json(url: str, headers: dict[str, str], timeout: float) -> dict[str, object]:
            captured["url"] = url
            captured["headers"] = headers
            captured["timeout"] = timeout
            return {
                "web": {
                    "results": [
                        {
                            "title": "FAA result",
                            "url": "https://faa.gov/uas",
                            "description": "FAA UAS guidance",
                        }
                    ]
                }
            }

        provider = BraveSearchProvider(
            api_key="test-key",
            api_url="https://search.example/api",
            fetch_json=fake_fetch_json,
        )

        result = await web_search(
            Settings.from_env({}),
            query="FAA UAS guidance",
            provider=provider,
        )

        self.assertEqual("https://faa.gov/uas", result.results[0].url)
        self.assertIn("q=FAA+UAS+guidance", captured["url"])
        self.assertEqual("test-key", captured["headers"]["X-Subscription-Token"])

    async def test_search_rejects_live_provider_without_key(self) -> None:
        with self.assertRaisesRegex(SearchProviderError, "search_api_key_required"):
            await web_search(
                Settings.from_env({"SEARCH_PROVIDER": "brave"}),
                query="FAA UAS guidance",
            )

    async def test_search_rejects_unknown_provider(self) -> None:
        with self.assertRaisesRegex(SearchProviderError, "unsupported_search_provider"):
            await web_search(
                Settings.from_env({"SEARCH_PROVIDER": "mystery"}),
                query="FAA UAS guidance",
            )


if __name__ == "__main__":
    unittest.main()
