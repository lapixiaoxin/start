"""Tiny command-line demo for PyHelixent."""

from __future__ import annotations

import argparse
from pathlib import Path

from pyhelixent.coding import create_coding_agent
from pyhelixent.foundation import AssistantMessage, RuleBasedLearningModel, ToolMessage, message_text


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the PyHelixent learning agent.")
    parser.add_argument("message", nargs="*", help="Message to send to the demo agent.")
    parser.add_argument("--workspace", default=".", help="Workspace root for coding tools.")
    args = parser.parse_args(argv)

    user_message = " ".join(args.message).strip() or "list files"
    agent = create_coding_agent(
        model=RuleBasedLearningModel(),
        workspace_root=Path(args.workspace),
    )

    for event in agent.stream(user_message):
        if event.type != "message" or event.message is None:
            continue
        if isinstance(event.message, AssistantMessage):
            print(f"assistant: {message_text(event.message)}")
        elif isinstance(event.message, ToolMessage):
            print(f"tool: {message_text(event.message)}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

