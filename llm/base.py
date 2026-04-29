"""Base LLM client interface."""

from abc import ABC, abstractmethod
from typing import Any, Generator
from dataclasses import dataclass


@dataclass
class LLMResponse:
    """Response from LLM."""

    content: str
    thinking: str | None = None
    thinking_signature: str | None = None
    tool_calls: list[dict[str, Any]] | None = None
    finish_reason: str = "stop"
    usage: dict[str, int] | None = None

    @property
    def has_tool_calls(self) -> bool:
        """Check if response contains tool calls."""
        return bool(self.tool_calls)


class BaseLLM(ABC):
    """Abstract base class for LLM clients."""

    def __init__(self, config):
        self.config = config

    @abstractmethod
    def chat(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
    ) -> LLMResponse:
        """Send a chat request and return the response."""
        pass

    @abstractmethod
    def chat_stream(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
    ) -> Generator[str, None, LLMResponse]:
        """Stream a chat response, yielding content chunks."""
        pass

    @abstractmethod
    def validate_connection(self) -> tuple[bool, str]:
        """Validate the API connection."""
        pass
