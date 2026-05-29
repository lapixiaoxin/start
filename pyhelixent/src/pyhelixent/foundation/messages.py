"""Conversation message and content primitives."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal, TypeAlias
from uuid import uuid4


@dataclass(slots=True)
class TextContent:
    """Plain assistant or user-visible text."""

    text: str
    type: Literal["text"] = field(default="text", init=False)


@dataclass(slots=True)
class ToolUseContent:
    """A model request to invoke a named tool."""

    name: str
    input: dict[str, Any] = field(default_factory=dict)
    id: str = field(default_factory=lambda: f"toolu_{uuid4().hex}")
    type: Literal["tool_use"] = field(default="tool_use", init=False)


@dataclass(slots=True)
class ToolResultContent:
    """Observation content produced by a tool invocation."""

    tool_use_id: str
    content: str
    type: Literal["tool_result"] = field(default="tool_result", init=False)


MessageContent: TypeAlias = TextContent | ToolUseContent | ToolResultContent


@dataclass(slots=True)
class UserMessage:
    """A message supplied by the user."""

    content: list[TextContent]
    role: Literal["user"] = field(default="user", init=False)

    @classmethod
    def from_text(cls, text: str) -> "UserMessage":
        return cls(content=[TextContent(text)])


@dataclass(slots=True)
class AssistantMessage:
    """A model response that may include text and tool calls."""

    content: list[TextContent | ToolUseContent]
    streaming: bool = False
    role: Literal["assistant"] = field(default="assistant", init=False)

    @classmethod
    def from_text(cls, text: str, *, streaming: bool = False) -> "AssistantMessage":
        return cls(content=[TextContent(text)], streaming=streaming)


@dataclass(slots=True)
class ToolMessage:
    """A tool observation appended to the transcript."""

    content: list[ToolResultContent]
    role: Literal["tool"] = field(default="tool", init=False)


NonSystemMessage: TypeAlias = UserMessage | AssistantMessage | ToolMessage


def text_content(text: str) -> list[TextContent]:
    """Create message content from plain text."""

    return [TextContent(text)]


def message_text(message: NonSystemMessage) -> str:
    """Return all textual content from a message."""

    parts: list[str] = []
    for item in message.content:
        if isinstance(item, TextContent):
            parts.append(item.text)
        elif isinstance(item, ToolResultContent):
            parts.append(item.content)
    return "\n".join(parts)


def iter_tool_uses(message: AssistantMessage) -> list[ToolUseContent]:
    """Extract tool calls from an assistant message."""

    return [item for item in message.content if isinstance(item, ToolUseContent)]

