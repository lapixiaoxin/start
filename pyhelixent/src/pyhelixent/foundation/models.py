"""Model contracts and deterministic learning models."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, Protocol

from pyhelixent.foundation.messages import (
    AssistantMessage,
    NonSystemMessage,
    TextContent,
    ToolUseContent,
    message_text,
)
from pyhelixent.foundation.tools import Tool


@dataclass(slots=True)
class ModelContext:
    """Input passed from the agent loop to a model."""

    prompt: str
    messages: list[NonSystemMessage]
    tools: list[Tool] = field(default_factory=list)


class Model(Protocol):
    """A provider-neutral model interface."""

    def stream(self, context: ModelContext) -> Iterable[AssistantMessage]:
        """Yield assistant snapshots and finish with the final message."""


class ScriptedModel:
    """A deterministic model useful for tests and examples."""

    def __init__(self, responses: Iterable[AssistantMessage]) -> None:
        self._responses = list(responses)
        self._index = 0

    def stream(self, context: ModelContext) -> Iterable[AssistantMessage]:
        if self._index >= len(self._responses):
            raise RuntimeError("ScriptedModel has no response left")
        response = self._responses[self._index]
        self._index += 1
        yield response


class RuleBasedLearningModel:
    """A tiny deterministic model that demonstrates tool-calling flow."""

    def stream(self, context: ModelContext) -> Iterable[AssistantMessage]:
        if context.messages and context.messages[-1].role == "tool":
            observation = message_text(context.messages[-1])
            yield AssistantMessage.from_text(f"Observation received:\n{observation}")
            return

        text = message_text(context.messages[-1]).lower() if context.messages else ""
        tool_names = {tool.name for tool in context.tools}

        if "list" in text and "list_files" in tool_names:
            yield AssistantMessage(
                content=[
                    TextContent("I will inspect the workspace files."),
                    ToolUseContent(name="list_files", input={"path": ".", "recursive": False}),
                ]
            )
            return

        if ("grep" in text or "search" in text) and "grep_search" in tool_names:
            pattern = text.split("for", 1)[-1].strip() if "for" in text else text
            yield AssistantMessage(
                content=[
                    TextContent("I will search the workspace."),
                    ToolUseContent(name="grep_search", input={"path": ".", "pattern": pattern or "agent"}),
                ]
            )
            return

        yield AssistantMessage.from_text(
            "This demo model is deterministic. Try asking it to list files or search for text."
        )

