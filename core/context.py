"""Context window management for Xagent."""

from dataclasses import dataclass
from typing import Any

import tiktoken


@dataclass
class ContextConfig:
    """Configuration for context management."""

    max_context_tokens: int = 128000  # Model's max context
    reserve_tokens: int = 4096  # Reserve for response
    summary_threshold: float = 0.8  # Summarize when 80% full


class ContextManager:
    """Manages context window and token counting."""

    def __init__(self, config: ContextConfig | None = None, model: str = "gpt-4o"):
        self.config = config or ContextConfig()
        self.model = model
        self._encoder = None

    @property
    def encoder(self):
        """Lazy load tiktoken encoder."""
        if self._encoder is None:
            try:
                self._encoder = tiktoken.encoding_for_model(self.model)
            except KeyError:
                # Fallback for unknown models
                self._encoder = tiktoken.get_encoding("cl100k_base")
        return self._encoder

    def count_tokens(self, text: str) -> int:
        """Count tokens in text."""
        return len(self.encoder.encode(text))

    def count_message_tokens(self, message: dict[str, Any]) -> int:
        """Count tokens in a message."""
        tokens = 4  # Message overhead
        for key, value in message.items():
            if isinstance(value, str):
                tokens += self.count_tokens(value)
            elif isinstance(value, list):
                # Tool calls
                for item in value:
                    tokens += self.count_tokens(str(item))
        return tokens

    def count_messages_tokens(self, messages: list[dict[str, Any]]) -> int:
        """Count total tokens in messages."""
        total = 3  # Priming tokens
        for msg in messages:
            total += self.count_message_tokens(msg)
        return total

    def available_tokens(self, current_tokens: int) -> int:
        """Calculate available tokens for response."""
        max_allowed = self.config.max_context_tokens - self.config.reserve_tokens
        return max(0, max_allowed - current_tokens)

    def needs_compression(self, messages: list[dict[str, Any]]) -> bool:
        """Check if messages need compression."""
        current = self.count_messages_tokens(messages)
        threshold = self.config.max_context_tokens * self.config.summary_threshold
        return current > threshold

    def compress_messages(
        self,
        messages: list[dict[str, Any]],
        keep_recent: int = 4,
    ) -> list[dict[str, Any]]:
        """Compress messages by summarizing old ones.

        Args:
            messages: List of messages
            keep_recent: Number of recent messages to keep intact

        Returns:
            Compressed messages list
        """
        if len(messages) <= keep_recent + 1:  # +1 for system
            return messages

        # Keep system message
        system_msg = None
        other_msgs = []
        for msg in messages:
            if msg["role"] == "system":
                system_msg = msg
            else:
                other_msgs.append(msg)

        if len(other_msgs) <= keep_recent:
            return messages

        # Split into old and recent
        old_msgs = other_msgs[:-keep_recent]
        recent_msgs = other_msgs[-keep_recent:]

        # Create summary of old messages
        summary_parts = []
        for msg in old_msgs:
            role = msg["role"]
            content = msg.get("content", "")
            if role == "user":
                # Truncate long user messages
                if len(content) > 200:
                    content = content[:200] + "..."
                summary_parts.append(f"User: {content}")
            elif role == "assistant":
                # Summarize assistant responses
                if len(content) > 100:
                    content = content[:100] + "..."
                summary_parts.append(f"Assistant: {content}")
            elif role == "tool":
                name = msg.get("name", "tool")
                summary_parts.append(f"[Tool {name} called]")

        summary = "\n".join(summary_parts)
        summary_msg = {
            "role": "user",
            "content": f"[Previous conversation summary]\n{summary}\n[End of summary]",
        }

        # Rebuild messages
        result = []
        if system_msg:
            result.append(system_msg)
        result.append(summary_msg)
        result.extend(recent_msgs)

        return result

    def truncate_content(self, content: str, max_tokens: int) -> str:
        """Truncate content to fit within token limit."""
        tokens = self.encoder.encode(content)
        if len(tokens) <= max_tokens:
            return content

        truncated = self.encoder.decode(tokens[:max_tokens])
        return truncated + f"\n... (truncated, {len(tokens) - max_tokens} tokens omitted)"


class TokenBudget:
    """Track token usage with a budget."""

    def __init__(self, budget: int = 100000):
        self.budget = budget
        self.used = 0

    def use(self, tokens: int) -> bool:
        """Use tokens from budget. Returns False if over budget."""
        self.used += tokens
        return self.used <= self.budget

    def remaining(self) -> int:
        """Get remaining tokens."""
        return max(0, self.budget - self.used)

    def is_over_budget(self) -> bool:
        """Check if over budget."""
        return self.used > self.budget

    def reset(self) -> None:
        """Reset usage."""
        self.used = 0

    def __str__(self) -> str:
        return f"TokenBudget({self.used}/{self.budget})"
