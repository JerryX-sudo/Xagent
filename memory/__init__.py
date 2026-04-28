"""Memory system for Xagent."""

from memory.dynamic import DynamicMemory, ConsolidationTrigger, MemoryEntry
from memory.static import StaticMemory

__all__ = ["DynamicMemory", "StaticMemory", "ConsolidationTrigger", "MemoryEntry"]


def get_memory_manager():
    """Get both memory managers."""
    return DynamicMemory(), StaticMemory()
