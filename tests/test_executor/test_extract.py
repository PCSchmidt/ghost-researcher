"""Regression tests for extract_structured_data."""

from __future__ import annotations

import unittest
from contextlib import asynccontextmanager

from backend.config import Settings
from backend.executor.extract import extract_structured_data


class FakeExtractPage:
    def __init__(self, values: list[str]) -> None:
        self.values = values
        self.selector: str | None = None

    async def eval_on_selector_all(self, selector: str, expression: str) -> list[str]:
        self.selector = selector
        return self.values

    async def evaluate(self, expression: str, *args: object) -> object:
        selectors = args[0] if args else ["body"]
        selector = selectors[0] if isinstance(selectors, list) and selectors else "body"
        return [{"selector": selector, "text": "\n".join(self.values)}]

    async def wait_for_timeout(self, ms: float) -> None:
        pass

    async def wait_for_load_state(self, *args, **kwargs) -> None:
        pass

    async def content(self) -> str:
        return ""


class ExtractStructuredDataTests(unittest.IsolatedAsyncioTestCase):
    async def test_extract_returns_normalized_records(self) -> None:
        page = FakeExtractPage(["  First item  ", "Second\nitem", ""])

        @asynccontextmanager
        async def fake_context(settings: Settings):
            yield page

        result = await extract_structured_data(
            Settings.from_env({}),
            selector="article",
            extraction_goal="collect article text",
            page_context_factory=fake_context,
        )

        self.assertEqual(1, result.record_count)
        self.assertEqual("First item Second item", result.records[0]["text"])
        self.assertEqual("article", result.records[0]["selector"])
        self.assertEqual("First item Second item", result.text_excerpt)
        self.assertTrue(result.schema_valid)

    async def test_extract_marks_schema_invalid_when_required_field_missing(self) -> None:
        page = FakeExtractPage(["Only text"])

        @asynccontextmanager
        async def fake_context(settings: Settings):
            yield page

        result = await extract_structured_data(
            Settings.from_env({}),
            selector=".result",
            extraction_goal="collect title",
            output_schema={"required": ["title"]},
            page_context_factory=fake_context,
        )

        self.assertFalse(result.schema_valid)

    async def test_extract_collects_multiple_content_sections(self) -> None:
        class SectionPage(FakeExtractPage):
            async def evaluate(self, expression: str, *args: object) -> object:
                return [
                    {"selector": "article", "text": "Article analysis with 2026 findings"},
                    {"selector": "main", "text": "Main page context and source links"},
                    {"selector": "body", "text": "Article analysis with 2026 findings"},
                ]

        page = SectionPage([])

        @asynccontextmanager
        async def fake_context(settings: Settings):
            yield page

        result = await extract_structured_data(
            Settings.from_env({}),
            selector="article",
            extraction_goal="collect article sections",
            page_context_factory=fake_context,
        )

        self.assertEqual(2, result.record_count)
        self.assertEqual(["article", "main"], [record["selector"] for record in result.records])
        self.assertIn("Main page context", result.text_excerpt)

    async def test_extract_includes_metadata_record(self) -> None:
        class MetadataPage(FakeExtractPage):
            async def evaluate(self, expression: str, *args: object) -> object:
                return {
                    "sections": [{"selector": "article", "text": "Article body text"}],
                    "metadata": {
                        "title": "Agency Report",
                        "description": "Official report description",
                        "published_time": "2026-06-01",
                        "canonical_url": "https://agency.gov/report",
                        "document_url": "https://agency.gov/report",
                        "content_type": "text/html",
                        "has_app_shell": False,
                        "body_text": "Article body text",
                    },
                }

        page = MetadataPage([])

        @asynccontextmanager
        async def fake_context(settings: Settings):
            yield page

        result = await extract_structured_data(
            Settings.from_env({}),
            selector="article",
            extraction_goal="collect report metadata",
            page_context_factory=fake_context,
        )

        self.assertEqual("metadata", result.records[0]["record_type"])
        self.assertEqual("Agency Report", result.records[0]["title"])
        self.assertIn("Official report description", result.text_excerpt)

    async def test_extract_records_hard_page_limitations(self) -> None:
        class HardPage(FakeExtractPage):
            def __init__(self, metadata: dict[str, object], body_text: str) -> None:
                super().__init__([])
                self.metadata = metadata
                self.body_text = body_text

            async def evaluate(self, expression: str, *args: object) -> object:
                payload = dict(self.metadata)
                payload["body_text"] = self.body_text
                return {"sections": [], "metadata": payload}

        cases = [
            (
                "pdf",
                HardPage(
                    {
                        "title": "PDF report",
                        "document_url": "https://agency.gov/report.pdf",
                        "content_type": "application/pdf",
                        "has_app_shell": False,
                    },
                    "PDF viewer",
                ),
            ),
            (
                "paywall",
                HardPage(
                    {
                        "title": "Members only report",
                        "document_url": "https://news.example/report",
                        "content_type": "text/html",
                        "has_app_shell": False,
                    },
                    "Please subscribe to continue reading this report.",
                ),
            ),
            (
                "spa_thin",
                HardPage(
                    {
                        "title": "Research app",
                        "document_url": "https://app.example/report",
                        "content_type": "text/html",
                        "has_app_shell": True,
                    },
                    "Loading",
                ),
            ),
        ]

        for expected_page_type, page in cases:
            with self.subTest(expected_page_type=expected_page_type):
                @asynccontextmanager
                async def fake_context(settings: Settings):
                    yield page

                result = await extract_structured_data(
                    Settings.from_env({}),
                    selector="article",
                    extraction_goal="collect hard page limitation",
                    page_context_factory=fake_context,
                )

                limitation = result.records[-1]
                self.assertEqual("limitation", limitation["record_type"])
                self.assertEqual(expected_page_type, limitation["page_type"])


if __name__ == "__main__":
    unittest.main()
