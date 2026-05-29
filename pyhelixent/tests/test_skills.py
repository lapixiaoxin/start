from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from pyhelixent.agent import AgentContext
from pyhelixent.foundation import ModelContext
from pyhelixent.skills import SkillsMiddleware, list_skills, read_skill_frontmatter


class SkillsTest(unittest.TestCase):
    def test_reads_skill_frontmatter(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            skill_file = Path(temp_dir) / "SKILL.md"
            skill_file.write_text(
                "---\nname: coding-plan\ndescription: Helps plan coding work.\n---\n# Body\n",
                encoding="utf-8",
            )

            skill = read_skill_frontmatter(skill_file)

            self.assertEqual(skill.name, "coding-plan")
            self.assertEqual(skill.description, "Helps plan coding work.")
            self.assertEqual(skill.path, str(skill_file))

    def test_discovers_skills_from_parent_directory(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            skills_dir = Path(temp_dir) / "skills"
            skill_dir = skills_dir / "example"
            skill_dir.mkdir(parents=True)
            (skill_dir / "SKILL.md").write_text(
                "---\nname: example\ndescription: Example skill.\n---\n",
                encoding="utf-8",
            )
            (skills_dir / "not-a-skill.txt").write_text("ignored", encoding="utf-8")

            skills = list_skills([skills_dir])

            self.assertEqual(len(skills), 1)
            self.assertEqual(skills[0].name, "example")

    def test_skills_middleware_injects_prompt(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            skills_dir = Path(temp_dir) / "skills"
            skill_dir = skills_dir / "example"
            skill_dir.mkdir(parents=True)
            (skill_dir / "SKILL.md").write_text(
                "---\nname: example\ndescription: Example skill.\n---\n",
                encoding="utf-8",
            )
            middleware = SkillsMiddleware([skills_dir])
            agent_context = AgentContext(prompt="Base prompt", requested_skill_name="example")
            agent_context.skills = middleware.before_agent_run(agent_context)["skills"]
            model_context = ModelContext(prompt="Base prompt", messages=[], tools=[])

            update = middleware.before_model(model_context, agent_context)

            self.assertIsNotNone(update)
            prompt = update["prompt"]
            self.assertIn("<skill_system>", prompt)
            self.assertIn('name="example"', prompt)
            self.assertIn("<explicit_skill_invocation>", prompt)


if __name__ == "__main__":
    unittest.main()

