"""Middleware that exposes skills to the model prompt."""

from __future__ import annotations

from pathlib import Path

from pyhelixent.agent import AgentContext
from pyhelixent.foundation import ModelContext
from pyhelixent.skills.loader import list_skills


class SkillsMiddleware:
    """Load skills and inject their metadata into the model prompt."""

    def __init__(self, skills_dirs: list[str | Path] | None = None) -> None:
        self.skills_dirs = list(skills_dirs or [Path.cwd() / "skills"])

    def before_agent_run(self, agent_context: AgentContext) -> dict[str, object]:
        return {"skills": list_skills(self.skills_dirs)}

    def before_model(
        self,
        model_context: ModelContext,
        agent_context: AgentContext,
    ) -> dict[str, object] | None:
        if not agent_context.skills:
            return None

        requested = None
        if agent_context.requested_skill_name:
            needle = agent_context.requested_skill_name.lower()
            requested = next(
                (
                    skill
                    for skill in agent_context.skills
                    if skill.name and skill.name.lower() == needle
                ),
                None,
            )

        skills_xml = "\n".join(
            (
                f'<skill name="{skill.name or ""}" path="{skill.path}">\n'
                f"{skill.description or ''}\n"
                "</skill>"
            )
            for skill in agent_context.skills
        )
        requested_xml = ""
        if requested is not None:
            requested_xml = (
                "\n<explicit_skill_invocation>\n"
                f'The user explicitly requested "{requested.name}". '
                f'Read the skill file at "{requested.path}" before answering.\n'
                "</explicit_skill_invocation>\n"
            )

        prompt = (
            model_context.prompt
            + "\n\n<skill_system>\n"
            + "<instructions>\n"
            + "Use listed skills when they match the task. Load only the skill files you need.\n"
            + "</instructions>\n"
            + requested_xml
            + "<skills>\n"
            + skills_xml
            + "\n</skills>\n"
            + "</skill_system>"
        )
        return {"prompt": prompt}

