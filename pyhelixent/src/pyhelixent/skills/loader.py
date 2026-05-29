"""Discover and parse `SKILL.md` files."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass(frozen=True, slots=True)
class SkillFrontmatter:
    """Metadata loaded from a skill file."""

    path: str
    name: str | None = None
    description: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


def read_skill_frontmatter(path: str | Path) -> SkillFrontmatter:
    """Read YAML-like front matter from a `SKILL.md` file."""

    skill_path = Path(path)
    if not skill_path.exists():
        raise FileNotFoundError(f"File {skill_path} does not exist")

    data = _parse_frontmatter(skill_path.read_text(encoding="utf-8"))
    metadata = {key: value for key, value in data.items() if key not in {"name", "description"}}
    return SkillFrontmatter(
        path=str(skill_path),
        name=data.get("name"),
        description=data.get("description"),
        metadata=metadata,
    )


def list_skills(skills_dirs: list[str | Path]) -> list[SkillFrontmatter]:
    """Discover skills from one or more parent directories."""

    skills: list[SkillFrontmatter] = []
    seen: set[str] = set()

    for skills_dir in skills_dirs:
        root = Path(skills_dir).expanduser()
        if not root.exists() or not root.is_dir():
            continue

        for child in sorted(root.iterdir(), key=lambda item: item.name):
            if not child.is_dir():
                continue
            skill_file = child / "SKILL.md"
            if not skill_file.exists():
                continue
            resolved = str(skill_file.resolve())
            if resolved in seen:
                continue
            seen.add(resolved)
            skills.append(read_skill_frontmatter(skill_file))

    return skills


def _parse_frontmatter(text: str) -> dict[str, str]:
    if not text.startswith("---"):
        return {}

    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}

    data: dict[str, str] = {}
    for line in lines[1:]:
        if line.strip() == "---":
            break
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        data[key.strip()] = _strip_scalar(value.strip())
    return data


def _strip_scalar(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        return value[1:-1]
    return value

