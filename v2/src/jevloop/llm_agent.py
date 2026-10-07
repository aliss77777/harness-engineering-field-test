"""A model-backed agent: the Cheap agent and the Strong agent are both this, with different models.

Version 0 uses the bench's own system prompt unchanged. The Agent skill loop (Phase 1) will
append a learned skill file to it. The loop mirrors the bench's runner: each step is one model
response; its tool calls run in order and their results go back to the model; the run ends when
the model replies without tool calls or after `max_steps` responses.
"""
from __future__ import annotations

import json
from typing import Any

from jevloop.bench import PublicTask
from jevloop.openrouter import ChatClient, ContentBlockedError
from jevloop.runs import AgentResult, ToolBox

# Keys the provider needs back on the next turn (e.g. Gemini's reasoning signatures for tool calls).
_ASSISTANT_KEYS = ("role", "content", "tool_calls", "reasoning", "reasoning_details")


class LLMAgent:
    def __init__(self, name: str, client: ChatClient, *, max_steps: int = 50, skill: str | None = None):
        self.name = name
        self.client = client
        self.max_steps = max_steps
        self.skill = skill

    def _start(self, task: PublicTask) -> list[dict[str, Any]]:
        messages = [dict(m) for m in task.messages]
        if self.skill:
            messages[0]["content"] = messages[0]["content"] + "\n\n" + self.skill
        return messages

    def run(self, task: PublicTask, tools: ToolBox, candidate: int) -> AgentResult:
        messages = self._start(task)
        result = AgentResult(stop_reason="max_steps")
        schemas = tools.schemas()
        for step in range(self.max_steps):
            try:
                reply = self.client.complete(
                    messages, schemas,
                    cache_key={"agent": self.name, "task_id": task.task_id, "candidate": candidate},
                    event={"event": "agent_turn", "agent": self.name, "task_id": task.task_id,
                           "candidate": candidate, "step": step},
                )
            except ContentBlockedError as error:
                result.stop_reason, result.final_message = "error", f"content blocked: {error}"
                return result
            usage = reply["usage"]
            result.steps = step + 1
            result.model_calls += 1
            result.input_tokens += usage["input_tokens"]
            result.output_tokens += usage["output_tokens"]
            result.cost_usd += usage["cost"]
            result.model_seconds += usage["latency_ms"] / 1000
            message = reply["message"]
            messages.append({k: message[k] for k in _ASSISTANT_KEYS if message.get(k) is not None} | {"role": "assistant"})
            calls = message.get("tool_calls") or []
            if not calls:
                result.final_message = message.get("content") or ""
                result.stop_reason = "done"
                return result
            for call in calls:
                function = call.get("function") or {}
                try:
                    args = json.loads(function.get("arguments") or "{}")
                    if not isinstance(args, dict):
                        raise ValueError("arguments are not a JSON object")
                    output = tools.call(function.get("name", ""), args)
                except (ValueError, TypeError) as error:
                    result.parse_errors += 1
                    output = json.dumps({"error": {"code": 400, "message": f"could not parse tool arguments: {error}"}})
                messages.append({"role": "tool", "tool_call_id": call.get("id", ""), "content": output})
        return result
