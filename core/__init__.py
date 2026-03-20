"""Core components for Xagent."""

from core.config import Config
from core.session import Session
from core.cache import RequestCache
from core.prompts import SYSTEM_PROMPT, MEMORY_INJECTION_TEMPLATE, SKILL_PROMPT_TEMPLATE
from core.skills import Skill, SkillRegistry
from core.permission import PermissionManager

__all__ = [
    "Config",
    "Session",
    "RequestCache",
    "SYSTEM_PROMPT",
    "MEMORY_INJECTION_TEMPLATE",
    "SKILL_PROMPT_TEMPLATE",
    "Skill",
    "SkillRegistry",
    "PermissionManager",
]


def get_agent():
    """Lazy import Agent to avoid circular imports."""
    from core.agent import Agent
    return Agent
