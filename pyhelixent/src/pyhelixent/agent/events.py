"""Events emitted by the agent loop."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from pyhelixent.foundation.messages import NonSystemMessage


@dataclass(slots=True)
class AgentEvent:
    """A streaming event from an agent run."""

    type: str
    message: NonSystemMessage | None = None
    subtype: str | None = None
    name: str | None = None
    input: dict[str, Any] | None = None

