"""A small ReAct-style agent loop."""

from __future__ import annotations

from concurrent.futures import Future, ThreadPoolExecutor, as_completed
from typing import Any, Iterable

from pyhelixent.agent.events import AgentEvent
from pyhelixent.agent.middleware import AgentContext, SkipToolUse
from pyhelixent.foundation import (
    AssistantMessage,
    Model,
    ModelContext,
    Tool,
    ToolMessage,
    ToolResultContent,
    ToolUseContent,
    UserMessage,
    format_tool_result,
    iter_tool_uses,
)


class Agent:
    """Runs a generic ReAct loop over a provider-neutral model."""

    def __init__(
        self,
        *,
        model: Model,
        prompt: str,
        name: str | None = None,
        messages: list[Any] | None = None,
        tools: list[Tool] | None = None,
        middlewares: list[Any] | None = None,
        max_steps: int = 100,
        max_workers: int | None = None,
    ) -> None:
        self.name = name
        self.model = model
        self.middlewares = middlewares or []
        self.max_steps = max_steps
        self.max_workers = max_workers
        self._context = AgentContext(
            prompt=prompt,
            messages=list(messages or []),
            tools=list(tools or []),
        )
        self._streaming = False

    @property
    def messages(self) -> list[Any]:
        return self._context.messages

    @property
    def prompt(self) -> str:
        return self._context.prompt

    @prompt.setter
    def prompt(self, value: str) -> None:
        self._context.prompt = value

    @property
    def tools(self) -> list[Tool]:
        return self._context.tools

    @property
    def streaming(self) -> bool:
        return self._streaming

    def set_requested_skill_name(self, name: str | None) -> None:
        self._context.requested_skill_name = name

    def clear_messages(self) -> None:
        self._context.messages.clear()

    def run(self, message: str | UserMessage) -> AssistantMessage:
        """Run until completion and return the last assistant message."""

        latest: AssistantMessage | None = None
        for event in self.stream(message):
            if event.type == "message" and isinstance(event.message, AssistantMessage):
                latest = event.message
        if latest is None:
            raise RuntimeError("Agent run completed without an assistant message")
        return latest

    def stream(self, message: str | UserMessage) -> Iterable[AgentEvent]:
        """Yield events while running the ReAct loop."""

        if self._streaming:
            raise RuntimeError("Agent is already streaming")

        user_message = message if isinstance(message, UserMessage) else UserMessage.from_text(message)
        self._append_message(user_message)
        self._before_agent_run()
        self._streaming = True

        try:
            for step in range(1, self.max_steps + 1):
                self._before_agent_step(step)
                assistant_message = yield from self._think()
                self._after_model(assistant_message)
                yield AgentEvent(type="message", message=assistant_message)

                tool_uses = iter_tool_uses(assistant_message)
                if not tool_uses:
                    self._after_agent_run()
                    return

                yield from self._act(tool_uses)
                self._after_agent_step(step)
            raise RuntimeError("Maximum number of steps reached")
        finally:
            self._streaming = False

    def _think(self) -> Iterable[AgentEvent]:
        model_context = ModelContext(
            prompt=self.prompt,
            messages=self.messages,
            tools=self.tools,
        )
        self._before_model(model_context)

        latest: AssistantMessage | None = None
        for snapshot in self.model.stream(model_context):
            latest = snapshot
            if snapshot.streaming:
                yield self._derive_progress(snapshot)

        if latest is None:
            raise RuntimeError("Model stream ended without producing a message")

        latest.streaming = False
        self._append_message(latest)
        return latest

    def _derive_progress(self, snapshot: AssistantMessage) -> AgentEvent:
        tool_uses = iter_tool_uses(snapshot)
        if not tool_uses:
            return AgentEvent(type="progress", subtype="thinking")
        latest_tool = tool_uses[-1]
        return AgentEvent(
            type="progress",
            subtype="tool",
            name=latest_tool.name,
            input=latest_tool.input,
        )

    def _act(self, tool_uses: list[ToolUseContent]) -> Iterable[AgentEvent]:
        max_workers = self.max_workers or max(1, len(tool_uses))
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures: dict[Future[Any], tuple[ToolUseContent, str]] = {}

            for tool_use in tool_uses:
                tool = self._find_tool(tool_use.name)
                if tool is None:
                    self._append_tool_result(tool_use, f"Error: Tool {tool_use.name} not found")
                    yield AgentEvent(type="message", message=self.messages[-1])
                    continue

                before_result = self._before_tool_use(tool_use)
                if isinstance(before_result, SkipToolUse):
                    self._append_tool_result(tool_use, before_result.result)
                    yield AgentEvent(type="message", message=self.messages[-1])
                    continue

                future = executor.submit(tool.run, tool_use.input)
                futures[future] = (tool_use, tool.name)

            for future in as_completed(futures):
                tool_use, _tool_name = futures[future]
                try:
                    result = future.result()
                    self._after_tool_use(tool_use, result)
                except Exception as exc:
                    result = f"Error: {exc}"
                self._append_tool_result(tool_use, result)
                yield AgentEvent(type="message", message=self.messages[-1])

    def _find_tool(self, name: str) -> Tool | None:
        return next((tool for tool in self.tools if tool.name == name), None)

    def _append_message(self, message: Any) -> None:
        self.messages.append(message)

    def _append_tool_result(self, tool_use: ToolUseContent, result: Any) -> None:
        self._append_message(
            ToolMessage(
                content=[
                    ToolResultContent(
                        tool_use_id=tool_use.id,
                        content=format_tool_result(result),
                    )
                ]
            )
        )

    def _before_agent_run(self) -> None:
        self._run_context_hook("before_agent_run", self._context)

    def _after_agent_run(self) -> None:
        self._run_context_hook("after_agent_run", self._context)

    def _before_agent_step(self, step: int) -> None:
        self._run_context_hook("before_agent_step", self._context, step)

    def _after_agent_step(self, step: int) -> None:
        self._run_context_hook("after_agent_step", self._context, step)

    def _before_model(self, model_context: ModelContext) -> None:
        for middleware in self.middlewares:
            hook = getattr(middleware, "before_model", None)
            if hook is None:
                continue
            self._merge(model_context, hook(model_context, self._context))

    def _after_model(self, message: AssistantMessage) -> None:
        for middleware in self.middlewares:
            hook = getattr(middleware, "after_model", None)
            if hook is None:
                continue
            self._merge(message, hook(self._context, message))

    def _before_tool_use(self, tool_use: ToolUseContent) -> SkipToolUse | None:
        for middleware in self.middlewares:
            hook = getattr(middleware, "before_tool_use", None)
            if hook is None:
                continue
            result = hook(self._context, tool_use)
            if isinstance(result, SkipToolUse):
                return result
            self._merge(self._context, result)
        return None

    def _after_tool_use(self, tool_use: ToolUseContent, tool_result: Any) -> None:
        for middleware in self.middlewares:
            hook = getattr(middleware, "after_tool_use", None)
            if hook is None:
                continue
            self._merge(self._context, hook(self._context, tool_use, tool_result))

    def _run_context_hook(self, name: str, *args: Any) -> None:
        for middleware in self.middlewares:
            hook = getattr(middleware, name, None)
            if hook is None:
                continue
            self._merge(self._context, hook(*args))

    def _merge(self, target: Any, updates: dict[str, Any] | None) -> None:
        if not updates:
            return
        for key, value in updates.items():
            setattr(target, key, value)

