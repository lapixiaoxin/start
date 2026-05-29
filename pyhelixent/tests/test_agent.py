from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from pyhelixent.agent import Agent, AgentContext, SkipToolUse
from pyhelixent.foundation import (
    AssistantMessage,
    ModelContext,
    ScriptedModel,
    TextContent,
    ToolUseContent,
    define_tool,
    message_text,
)


class AgentLoopTest(unittest.TestCase):
    def test_agent_runs_tool_and_continues_until_final_answer(self) -> None:
        tool_use = ToolUseContent(name="echo", input={"text": "hello"}, id="call_1")
        model = ScriptedModel(
            [
                AssistantMessage(content=[TextContent("I will use a tool."), tool_use]),
                AssistantMessage.from_text("Done."),
            ]
        )
        tool = define_tool(
            name="echo",
            description="Echo input text.",
            invoke=lambda input: {"heard": input["text"]},
        )
        agent = Agent(model=model, prompt="test", tools=[tool], max_steps=3)

        events = list(agent.stream("say hello"))

        self.assertEqual([message.role for message in agent.messages], ["user", "assistant", "tool", "assistant"])
        self.assertEqual(message_text(agent.messages[-1]), "Done.")
        self.assertIn('"heard": "hello"', message_text(agent.messages[2]))
        self.assertEqual(len([event for event in events if event.type == "message"]), 3)

    def test_before_tool_use_can_skip_execution(self) -> None:
        class BlockingMiddleware:
            def __init__(self) -> None:
                self.after_tool_calls = 0

            def before_tool_use(self, agent_context: AgentContext, tool_use: ToolUseContent) -> SkipToolUse:
                return SkipToolUse(result={"blocked": tool_use.name})

            def after_tool_use(self, agent_context: AgentContext, tool_use: ToolUseContent, tool_result: object) -> None:
                self.after_tool_calls += 1

        model = ScriptedModel(
            [
                AssistantMessage(content=[ToolUseContent(name="danger", input={}, id="call_1")]),
                AssistantMessage.from_text("Blocked."),
            ]
        )
        tool = define_tool(
            name="danger",
            description="Should not run.",
            invoke=lambda input: (_ for _ in ()).throw(AssertionError("tool should not run")),
        )
        middleware = BlockingMiddleware()
        agent = Agent(model=model, prompt="test", tools=[tool], middlewares=[middleware], max_steps=3)

        list(agent.stream("please run danger"))

        self.assertEqual(middleware.after_tool_calls, 0)
        self.assertIn('"blocked": "danger"', message_text(agent.messages[2]))

    def test_middleware_hooks_run_in_lifecycle_order(self) -> None:
        calls: list[str] = []

        class RecorderMiddleware:
            def before_agent_run(self, agent_context: AgentContext) -> None:
                calls.append("before_agent_run")

            def before_agent_step(self, agent_context: AgentContext, step: int) -> None:
                calls.append(f"before_agent_step:{step}")

            def before_model(self, model_context: ModelContext, agent_context: AgentContext) -> None:
                calls.append("before_model")

            def after_model(self, agent_context: AgentContext, message: AssistantMessage) -> None:
                calls.append("after_model")

            def before_tool_use(self, agent_context: AgentContext, tool_use: ToolUseContent) -> None:
                calls.append("before_tool_use")

            def after_tool_use(self, agent_context: AgentContext, tool_use: ToolUseContent, tool_result: object) -> None:
                calls.append("after_tool_use")

            def after_agent_step(self, agent_context: AgentContext, step: int) -> None:
                calls.append(f"after_agent_step:{step}")

            def after_agent_run(self, agent_context: AgentContext) -> None:
                calls.append("after_agent_run")

        model = ScriptedModel(
            [
                AssistantMessage(content=[ToolUseContent(name="noop", input={}, id="call_1")]),
                AssistantMessage.from_text("Final."),
            ]
        )
        tool = define_tool(name="noop", description="No operation.", invoke=lambda input: "ok")
        agent = Agent(
            model=model,
            prompt="test",
            tools=[tool],
            middlewares=[RecorderMiddleware()],
            max_steps=3,
        )

        list(agent.stream("run"))

        self.assertEqual(
            calls,
            [
                "before_agent_run",
                "before_agent_step:1",
                "before_model",
                "after_model",
                "before_tool_use",
                "after_tool_use",
                "after_agent_step:1",
                "before_agent_step:2",
                "before_model",
                "after_model",
                "after_agent_run",
            ],
        )


if __name__ == "__main__":
    unittest.main()

