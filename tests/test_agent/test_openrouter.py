"""Regression tests for the OpenRouter planner adapter."""

from __future__ import annotations

import json
import unittest
from unittest.mock import patch
from typing import Any

from backend.agent.memory import AgentSession
from backend.agent.openrouter import OpenRouterChatClient, OpenRouterPlanner, PlannerAdapterError
from backend.config import Settings


def _tool_response(name: str, arguments: dict[str, Any], *, cost: float = 0.001) -> dict[str, Any]:
    return {
        "model": "deepseek/deepseek-v4-flash",
        "choices": [
            {
                "message": {
                    "tool_calls": [
                        {
                            "type": "function",
                            "function": {
                                "name": name,
                                "arguments": json.dumps(arguments),
                            },
                        }
                    ]
                }
            }
        ],
        "usage": {
            "prompt_tokens": 100,
            "completion_tokens": 20,
            "cost": cost,
        },
    }


class OpenRouterPlannerTests(unittest.IsolatedAsyncioTestCase):
    def test_chat_client_sends_bearer_key_and_requested_model(self) -> None:
        captured_requests: list[Any] = []

        class FakeResponse:
            def __enter__(self) -> "FakeResponse":
                return self

            def __exit__(self, exc_type, exc, tb) -> None:
                return None

            def read(self) -> bytes:
                return b'{"model":"deepseek/deepseek-v4-flash","choices":[]}'

        def fake_urlopen(http_request: Any, timeout: int) -> FakeResponse:
            captured_requests.append(http_request)
            return FakeResponse()

        settings = Settings.from_env({"OPENROUTER_API_KEY": "test-key"})
        client = OpenRouterChatClient(settings)

        with patch("backend.agent.openrouter.request.urlopen", side_effect=fake_urlopen):
            response = client._complete_sync({"model": settings.default_planner_model, "messages": []})

        self.assertEqual("deepseek/deepseek-v4-flash", response["model"])
        self.assertEqual(1, len(captured_requests))
        request_obj = captured_requests[0]
        self.assertEqual("Bearer test-key", request_obj.get_header("Authorization"))
        self.assertEqual(settings.openrouter_http_referer, request_obj.get_header("Http-referer"))
        self.assertEqual(settings.openrouter_app_title, request_obj.get_header("X-title"))
        self.assertEqual(
            "deepseek/deepseek-v4-flash",
            json.loads(request_obj.data.decode("utf-8"))["model"],
        )

    async def test_planner_returns_validated_tool_call_and_records_usage(self) -> None:
        captured_payloads: list[dict[str, Any]] = []

        async def fake_transport(payload: dict[str, Any]) -> dict[str, Any]:
            captured_payloads.append(payload)
            return _tool_response("web_search", {"query": "FAA BVLOS guidance", "num_results": 5})

        settings = Settings.from_env({})
        session = AgentSession(research_goal="FAA BVLOS guidance")
        planner = OpenRouterPlanner(settings, transport=fake_transport)

        decision = await planner.plan_next(session)

        self.assertEqual("web_search", decision.tool_call.name)
        self.assertEqual("FAA BVLOS guidance", decision.tool_call.arguments["query"])
        self.assertEqual(1, session.planner_turns)
        self.assertEqual(120, session.running_tokens)
        self.assertEqual(0.001, session.running_cost_usd)
        self.assertEqual(settings.default_planner_model, captured_payloads[0]["model"])
        self.assertEqual("required", captured_payloads[0]["tool_choice"])

    async def test_planner_rejects_free_text_without_tool_call(self) -> None:
        async def fake_transport(payload: dict[str, Any]) -> dict[str, Any]:
            return {
                "choices": [{"message": {"content": "Here is what I found."}}],
                "usage": {"prompt_tokens": 10, "completion_tokens": 8, "cost": 0.001},
            }

        planner = OpenRouterPlanner(Settings.from_env({}), transport=fake_transport)

        with self.assertRaisesRegex(PlannerAdapterError, "no_tool_calls_in_response"):
            await planner.plan_next(AgentSession(research_goal="FAA BVLOS guidance"))

    async def test_planner_rejects_invalid_tool_arguments(self) -> None:
        async def fake_transport(payload: dict[str, Any]) -> dict[str, Any]:
            return _tool_response("web_search", {"query": "FAA", "num_results": 20})

        planner = OpenRouterPlanner(Settings.from_env({}), transport=fake_transport)

        with self.assertRaisesRegex(PlannerAdapterError, "argument_above_maximum:num_results"):
            await planner.plan_next(AgentSession(research_goal="FAA BVLOS guidance"))

    async def test_finalize_report_returns_validated_tool_call(self) -> None:
        async def fake_transport(payload: dict[str, Any]) -> dict[str, Any]:
            return _tool_response(
                "finalize_report",
                {
                    "confidence": 0.84,
                    "sources_used": ["https://faa.gov/guidance"],
                    "termination_reason": "sufficient_coverage",
                },
            )

        planner = OpenRouterPlanner(Settings.from_env({}), transport=fake_transport)
        decision = await planner.plan_next(AgentSession(research_goal="FAA BVLOS guidance"))

        self.assertFalse(decision.should_stop)
        self.assertEqual("finalize_report", decision.tool_call.name)
        self.assertEqual("sufficient_coverage", decision.tool_call.arguments["termination_reason"])

    async def test_cost_limit_prevents_model_call(self) -> None:
        async def fake_transport(payload: dict[str, Any]) -> dict[str, Any]:
            self.fail("transport should not be called after cost limit")

        settings = Settings.from_env({"MAX_MODEL_COST_PER_JOB_USD": "0.05"})
        session = AgentSession(research_goal="FAA BVLOS guidance", running_cost_usd=0.05)
        planner = OpenRouterPlanner(settings, transport=fake_transport)

        decision = await planner.plan_next(session)

        self.assertTrue(decision.should_stop)
        self.assertEqual("cost_limit", decision.termination_reason)


if __name__ == "__main__":
    unittest.main()
