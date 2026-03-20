"""Skills system for Xagent."""

import importlib.util
from pathlib import Path
from dataclasses import dataclass, field
from typing import Any, Callable

from core.config import Config


@dataclass
class Skill:
    """A skill that can be invoked by name."""

    name: str
    description: str
    handler: Callable[..., str]
    parameters: dict[str, Any] = field(default_factory=dict)

    def run(self, **kwargs) -> str:
        """Execute the skill."""
        return self.handler(**kwargs)


class SkillRegistry:
    """Registry for managing skills."""

    def __init__(self):
        self._skills: dict[str, Skill] = {}
        self._register_builtin_skills()

    def _register_builtin_skills(self) -> None:
        """Register built-in skills."""
        # /help skill
        self.register(Skill(
            name="help",
            description="Show available commands and skills",
            handler=lambda: "Use /help to see available commands",
        ))

        # /summarize skill
        self.register(Skill(
            name="summarize",
            description="Summarize the current conversation",
            handler=lambda: "SKILL:summarize",  # Marker for agent to handle
        ))

        # /explain skill
        self.register(Skill(
            name="explain",
            description="Explain a concept or code",
            handler=lambda topic="": f"SKILL:explain:{topic}",
        ))

    def register(self, skill: Skill) -> None:
        """Register a skill."""
        self._skills[skill.name] = skill

    def get(self, name: str) -> Skill | None:
        """Get a skill by name."""
        return self._skills.get(name)

    def list_skills(self) -> list[str]:
        """List all registered skill names."""
        return list(self._skills.keys())

    def get_all(self) -> dict[str, Skill]:
        """Get all registered skills."""
        return self._skills.copy()

    def format_skills_list(self) -> str:
        """Format skills list for prompt injection."""
        lines = []
        for name, skill in self._skills.items():
            lines.append(f"- /{name}: {skill.description}")
        return "\n".join(lines)

    def load_skills_from_dir(self, skills_dir: Path | None = None) -> int:
        """Load skills from directory. Returns count of loaded skills."""
        if skills_dir is None:
            skills_dir = Config.get_config_dir() / "skills"

        if not skills_dir.exists():
            skills_dir.mkdir(parents=True, exist_ok=True)
            return 0

        count = 0
        for skill_file in skills_dir.glob("*.py"):
            if skill_file.name.startswith("_"):
                continue

            try:
                spec = importlib.util.spec_from_file_location(
                    skill_file.stem, skill_file
                )
                if spec and spec.loader:
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)

                    # Find Skill instances or create_skill functions
                    if hasattr(module, "skill") and isinstance(module.skill, Skill):
                        self.register(module.skill)
                        count += 1
                    elif hasattr(module, "create_skill"):
                        skill = module.create_skill()
                        if isinstance(skill, Skill):
                            self.register(skill)
                            count += 1

            except Exception as e:
                print(f"Warning: Failed to load skill {skill_file.name}: {e}")

        return count

    def execute(self, name: str, **kwargs) -> str | None:
        """Execute a skill by name."""
        skill = self.get(name)
        if not skill:
            return None
        return skill.run(**kwargs)
