"""Tool definitions and result formatting."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Callable


ToolInvoker = Callable[[dict[str, Any]], Any]


@dataclass(slots=True)
class Tool:
    """A callable action available to an agent."""

    name: str
    description: str
    invoke: ToolInvoker
    parameters: dict[str, Any] = field(default_factory=dict)

    def run(self, input: dict[str, Any] | None = None) -> Any:
        return self.invoke(input or {})


def define_tool(
    *,
    name: str,
    description: str,
    invoke: ToolInvoker,
    parameters: dict[str, Any] | None = None,
) -> Tool:
    """Define a function tool."""

    return Tool(
        name=name,
        description=description,
        parameters=parameters or {},
        invoke=invoke,
    )


def format_tool_result(result: Any) -> str:
    """Serialize a tool result into transcript-friendly text."""

    if isinstance(result, str):
        return result
    return json.dumps(result, ensure_ascii=False, indent=2, default=str)

