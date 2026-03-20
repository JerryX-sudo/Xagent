"""Tool implementations for Xagent."""

from tools.base import BaseTool

__all__ = ["BaseTool"]


def get_registry():
    """Lazy import ToolRegistry to avoid circular imports."""
    from tools.registry import ToolRegistry
    return ToolRegistry
