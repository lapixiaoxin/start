"""Factory for a small coding-oriented learning agent."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from pyhelixent.agent import Agent
from pyhelixent.coding.tools import default_coding_tools
from pyhelixent.foundation import Model
from pyhelixent.skills import SkillsMiddleware


DEFAULT_CODING_PROMPT = """You are PyHelixent, a small educational coding agent.
Use tools when they help. Explain observations clearly and keep actions inside the workspace."""


def create_coding_agent(
    *,
    model: Model,
    workspace_root: str | Path,
    skills_dirs: list[str | Path] | None = None,
    middlewares: list[Any] | None = None,
    max_steps: int = 8,
) -> Agent:
    """Wire the default prompt, coding tools, skills, and middlewares."""

    root = Path(workspace_root).resolve()
    middleware_chain = [SkillsMiddleware(skills_dirs or [root / "skills"])]
    middleware_chain.extend(middlewares or [])
    return Agent(
        name="pyhelixent-coding",
        model=model,
        prompt=DEFAULT_CODING_PROMPT,
        tools=default_coding_tools(root),
        middlewares=middleware_chain,
        max_steps=max_steps,
    )

