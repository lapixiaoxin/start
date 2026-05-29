"""Middleware contracts for the agent lifecycle."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from pyhelixent.foundation import AssistantMessage, ModelContext, NonSystemMessage, Tool, ToolUseContent


@dataclass(slots=True)
class AgentContext:
    """Mutable state threaded through an agent run."""

    prompt: str
    messages: list[NonSystemMessage] = field(default_factory=list)
    tools: list[Tool] = field(default_factory=list)
    skills: list[Any] = field(default_factory=list)
    requested_skill_name: str | None = None


@dataclass(frozen=True, slots=True)
class SkipToolUse:
    """Signal returned by `before_tool_use` to bypass a tool call."""

    result: Any


class AgentMiddleware:
    """Optional lifecycle hooks for an agent run."""

    def before_agent_run(self, agent_context: AgentContext) -> dict[str, Any] | None:
        return None

    def after_agent_run(self, agent_context: AgentContext) -> dict[str, Any] | None:
        return None

    def before_agent_step(self, agent_context: AgentContext, step: int) -> dict[str, Any] | None:
        return None

    def after_agent_step(self, agent_context: AgentContext, step: int) -> dict[str, Any] | None:
        return None

    def before_model(
        self,
        model_context: ModelContext,
        agent_context: AgentContext,
    ) -> dict[str, Any] | None:
        return None

    def after_model(
        self,
        agent_context: AgentContext,
        message: AssistantMessage,
    ) -> dict[str, Any] | None:
        return None

    def before_tool_use(
        self,
        agent_context: AgentContext,
        tool_use: ToolUseContent,
    ) -> dict[str, Any] | SkipToolUse | None:
        return None

    def after_tool_use(
        self,
        agent_context: AgentContext,
        tool_use: ToolUseContent,
        tool_result: Any,
    ) -> dict[str, Any] | None:
        return None
