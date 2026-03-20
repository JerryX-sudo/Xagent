"""Memory system for Xagent."""

from memory.dynamic import DynamicMemory
from memory.static import StaticMemory

__all__ = ["DynamicMemory", "StaticMemory"]


def get_memory_manager():
    """Get both memory managers."""
    return DynamicMemory(), StaticMemory()
