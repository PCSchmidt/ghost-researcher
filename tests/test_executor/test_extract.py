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


if __name__ == "__main__":
    unittest.main()
