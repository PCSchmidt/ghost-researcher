"""OpenRouter-backed planner adapter."""

from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from typing import Any, Awaitable, Callable
from urllib import error, request

from backend.agent.memory import AgentSession
from backend.agent.planner import PlannerDecision, ToolCall
from backend.agent.prompts import build_planner_messages
from backend.agent.tools import TOOLS, TOOL_REGISTRY
from backend.config import Settings

Transport = Callable[[dict[str, Any]], Awaitable[dict[str, Any]]]


class PlannerAdapterError(RuntimeError):
    """Raised when the model response cannot be accepted as a tool call."""


@dataclass(frozen=True, slots=True)
class ModelUsage:
    """Normalized usage metadata from a model response."""

    model: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    cost_usd: float = 0.0


class OpenRouterChatClient:
    """Small OpenAI-compatible chat completions client for OpenRouter."""

    def __init__(self, settings: Settings) -> None:
        if not settings.openrouter_api_key:
            raise ValueError("openrouter_api_key_required")
        self._settings = settings

    async def complete(self, payload: dict[str, Any]) -> dict[str, Any]:
        """POST a chat completion request and return decoded JSON."""
        return await asyncio.to_thread(self._complete_sync, payload)

    def _complete_sync(self, payload: dict[str, Any]) -> dict[str, Any]:
        url = self._settings.openrouter_base_url.rstrip("/") + "/chat/completions"
        body = json.dumps(payload).encode("utf-8")
        http_request = request.Request(
            url,
            data=body,
            method="POST",
            headers={
                "Authorization": f"Bearer {self._settings.openrouter_api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": self._settings.openrouter_http_referer,
                "X-Title": self._settings.openrouter_app_title,
            },
        )
        try:
            with request.urlopen(http_request, timeout=30) as response:
                return json.loads(response.read().decode("utf-8"))
        except error.URLError as exc:
            raise PlannerAdapterError("openrouter_request_failed") from exc
        except json.JSONDecodeError as exc:
            raise PlannerAdapterError("openrouter_invalid_json") from exc


class OpenRouterPlanner:
    """Planner that asks OpenRouter for one validated tool call."""

    def __init__(
        self,
        settings: Settings,
        *,
        transport: Transport | None = None,
        model: str | None = None,
    ) -> None:
        self._settings = settings
        self._model = model or settings.default_planner_model
        self._transport = transport or OpenRouterChatClient(settings).complete

    async def plan_next(
        self,
        session: AgentSession,
        *,
        last_tool_result: dict[str, Any] | None = None,
    ) -> PlannerDecision:
        """Return one validated model-planned decision."""
        if session.running_tokens >= self._settings.max_tokens_per_job:
            return PlannerDecision(tool_call=None, termination_reason="cost_limit")
        if session.running_cost_usd >= self._settings.max_model_cost_per_job_usd:
            return PlannerDecision(tool_call=None, termination_reason="cost_limit")

        response = await self._transport(self._request_payload(session, last_tool_result=last_tool_result))
        usage = _extract_usage(response, default_model=self._model)
        session.record_model_usage(
            prompt_tokens=usage.prompt_tokens,
            completion_tokens=usage.completion_tokens,
            cost_usd=usage.cost_usd,

        )
        if session.running_tokens >= self._settings.max_tokens_per_job:
            return PlannerDecision(tool_call=None, termination_reason="cost_limit")
        if session.running_cost_usd >= self._settings.max_model_cost_per_job_usd:
            return PlannerDecision(tool_call=None, termination_reason="cost_limit")

        # If the model returned plain text (no tool calls), retry once
        # with a stronger instruction. DeepSeek sometimes returns text
        # instead of a tool call after seeing search results.
        choices = response.get("choices") or []
        message = choices[0].get("message") if choices else {}
        if not (message.get("tool_calls")):
            # Retry with an explicit instruction to use tools.
            retry_payload = self._request_payload(session, last_tool_result=last_tool_result)
            retry_payload["messages"].append({
                "role": "user",
                "content": "You MUST call a tool. Do not return plain text. Pick navigate_to_url if there are unvisited source candidates, or web_search if you need more sources."
            })
            response = await self._transport(retry_payload)
            retry_usage = _extract_usage(response, default_model=self._model)
            session.record_model_usage(
                prompt_tokens=retry_usage.prompt_tokens,
                completion_tokens=retry_usage.completion_tokens,
                cost_usd=retry_usage.cost_usd,
            )
            choices = response.get("choices") or []
            message = choices[0].get("message") if choices else {}
            if not (message.get("tool_calls")):
                return PlannerDecision(tool_call=None, termination_reason="no_new_sources")
        return PlannerDecision(tool_call=_extract_tool_call(response))

    def _request_payload(
        self,
        session: AgentSession,
        *,
        last_tool_result: dict[str, Any] | None,
    ) -> dict[str, Any]:
        return {
            "model": self._model,
            "messages": build_planner_messages(session, last_tool_result=last_tool_result),
            "tools": [_to_openai_tool(tool) for tool in TOOLS],
            "tool_choice": "auto",
            "temperature": 0,
        }


def _to_openai_tool(tool: dict[str, Any]) -> dict[str, Any]:
    return {
        "type": "function",
        "function": {
            "name": tool["name"],
            "description": tool["description"],
            "parameters": tool["input_schema"],
        },
    }


def _extract_usage(response: dict[str, Any], *, default_model: str) -> ModelUsage:
    usage = response.get("usage") or {}
    cost_value = usage.get("cost") or usage.get("total_cost") or response.get("cost") or 0.0
    return ModelUsage(
        model=str(response.get("model") or default_model),
        prompt_tokens=int(usage.get("prompt_tokens") or 0),
        completion_tokens=int(usage.get("completion_tokens") or 0),
        cost_usd=float(cost_value),
    )


def _extract_tool_call(response: dict[str, Any]) -> ToolCall:
    choices = response.get("choices")
    if not isinstance(choices, list) or not choices:
        raise PlannerAdapterError("missing_choices")
    message = choices[0].get("message") if isinstance(choices[0], dict) else None
    if not isinstance(message, dict):
        raise PlannerAdapterError("missing_message")
    tool_calls = message.get("tool_calls")
    if not isinstance(tool_calls, list) or len(tool_calls) == 0:
        raise PlannerAdapterError("no_tool_calls_in_response")
    # Accept first tool call; some models (e.g. DeepSeek) return multiple in one turn.
    function = tool_calls[0].get("function") if isinstance(tool_calls[0], dict) else None
    if not isinstance(function, dict):
        raise PlannerAdapterError("missing_function_call")

    name = str(function.get("name") or "")
    raw_arguments = function.get("arguments") or "{}"
    if name not in TOOL_REGISTRY:
        raise PlannerAdapterError(f"unknown_tool:{name}")
    try:
        arguments = json.loads(raw_arguments) if isinstance(raw_arguments, str) else raw_arguments
    except json.JSONDecodeError as exc:
        raise PlannerAdapterError("invalid_tool_arguments_json") from exc
    if not isinstance(arguments, dict):
        raise PlannerAdapterError("invalid_tool_arguments")
    _validate_tool_arguments(name, arguments)
    return ToolCall(name=name, arguments=arguments)


def _validate_tool_arguments(name: str, arguments: dict[str, Any]) -> None:
    schema = TOOL_REGISTRY[name]["input_schema"]
    properties = schema.get("properties", {})
    for required_name in schema.get("required", []):
        if required_name not in arguments:
            raise PlannerAdapterError(f"missing_required_argument:{required_name}")

    for argument_name, value in arguments.items():
        if argument_name not in properties:
            raise PlannerAdapterError(f"unexpected_argument:{argument_name}")
        expected = properties[argument_name].get("type")
        if expected == "string" and not isinstance(value, str):
            raise PlannerAdapterError(f"invalid_argument_type:{argument_name}")
        if expected == "integer" and (not isinstance(value, int) or isinstance(value, bool)):
            raise PlannerAdapterError(f"invalid_argument_type:{argument_name}")
        if expected == "number" and (not isinstance(value, (int, float)) or isinstance(value, bool)):
            raise PlannerAdapterError(f"invalid_argument_type:{argument_name}")
        if expected == "array" and not isinstance(value, list):
            raise PlannerAdapterError(f"invalid_argument_type:{argument_name}")
        if expected == "object" and not isinstance(value, dict):
            raise PlannerAdapterError(f"invalid_argument_type:{argument_name}")
        minimum = properties[argument_name].get("minimum")
        maximum = properties[argument_name].get("maximum")
        if isinstance(value, (int, float)) and minimum is not None and value < minimum:
            raise PlannerAdapterError(f"argument_below_minimum:{argument_name}")
        if isinstance(value, (int, float)) and maximum is not None and value > maximum:
            raise PlannerAdapterError(f"argument_above_maximum:{argument_name}")


__all__ = [
    "ModelUsage",
    "OpenRouterChatClient",
    "OpenRouterPlanner",
    "PlannerAdapterError",
]
