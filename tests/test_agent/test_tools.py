"""Regression tests for the planner tool catalog."""

from __future__ import annotations

import unittest

from backend.agent.tools import TOOL_REGISTRY, TOOLS, get_tool


class ToolCatalogTests(unittest.TestCase):
    def test_expected_tool_names_exist(self) -> None:
        expected_names = {
            "navigate_to_url",
            "extract_structured_data",
            "web_search",
            "assess_credibility",
            "finalize_report",
        }
        self.assertEqual(expected_names, set(TOOL_REGISTRY))
        self.assertEqual(5, len(TOOLS))

    def test_each_tool_has_required_contract_sections(self) -> None:
        for tool in TOOLS:
            with self.subTest(tool=tool["name"]):
                self.assertIn("description", tool)
                self.assertIn("input_schema", tool)
                self.assertIn("output_schema", tool)
                self.assertIn("error_contract", tool)
                self.assertIsInstance(tool["error_contract"], list)
                self.assertGreater(len(tool["error_contract"]), 0)
                self.assertNotIn("pass", str(tool))
                self.assertNotIn("NotImplemented", str(tool))

    def test_finalize_report_supports_all_stop_reasons(self) -> None:
        finalize_report = get_tool("finalize_report")
        stop_reasons = finalize_report["input_schema"]["properties"]["termination_reason"]["enum"]
        self.assertEqual(
            [
                "sufficient_coverage",
                "max_steps",
                "cost_limit",
                "no_new_sources",
                "detection_blocked",
            ],
            stop_reasons,
        )

    def test_web_search_has_query_required(self) -> None:
        web_search = get_tool("web_search")
        self.assertEqual(["query"], web_search["input_schema"]["required"])


if __name__ == "__main__":
    unittest.main()
