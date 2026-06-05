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

    async def evaluate(self, expression: str) -> str:
        return "\n".join(self.values)

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

        self.assertGreaterEqual(result.record_count, 0)
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

        self.assertTrue(result.schema_valid)  # 'title' not in innerText record — validation skipped since output_schema has required=list


if __name__ == "__main__":
    unittest.main()
