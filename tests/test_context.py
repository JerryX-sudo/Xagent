"""Tests for context management module."""

import sys
from pathlib import Path

# Ensure correct path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest

from core.context import ContextManager, ContextConfig, TokenBudget


class TestContextManager:
    """Tests for ContextManager class."""

    def test_count_tokens(self):
        """Test token counting."""
        cm = ContextManager()
        count = cm.count_tokens("Hello, world!")
        assert count > 0
        assert count < 10  # Should be around 4 tokens

    def test_count_message_tokens(self):
        """Test counting message tokens."""
        cm = ContextManager()
        msg = {"role": "user", "content": "Hello, how are you?"}
        count = cm.count_message_tokens(msg)
        assert count > 0

    def test_count_messages_tokens(self):
        """Test counting multiple messages."""
        cm = ContextManager()
        messages = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there!"},
        ]
        count = cm.count_messages_tokens(messages)
        assert count > 0

    def test_needs_compression(self):
        """Test compression detection."""
        config = ContextConfig(max_context_tokens=100, summary_threshold=0.5)
        cm = ContextManager(config)

        # Small message shouldn't need compression
        small_msgs = [{"role": "user", "content": "Hi"}]
        assert cm.needs_compression(small_msgs) is False

        # Large message should need compression
        large_content = "word " * 1000
        large_msgs = [{"role": "user", "content": large_content}]
        assert cm.needs_compression(large_msgs) is True

    def test_compress_messages(self):
        """Test message compression."""
        cm = ContextManager()
        messages = [
            {"role": "system", "content": "You are helpful."},
            {"role": "user", "content": "Message 1"},
            {"role": "assistant", "content": "Response 1"},
            {"role": "user", "content": "Message 2"},
            {"role": "assistant", "content": "Response 2"},
            {"role": "user", "content": "Message 3"},
            {"role": "assistant", "content": "Response 3"},
        ]

        compressed = cm.compress_messages(messages, keep_recent=2)

        # Should keep system + summary + 2 recent
        assert len(compressed) <= 5
        # System message should be first
        assert compressed[0]["role"] == "system"

    def test_truncate_content(self):
        """Test content truncation."""
        cm = ContextManager()
        long_content = "word " * 1000

        truncated = cm.truncate_content(long_content, 100)
        # Check truncation happened
        assert "truncated" in truncated
        # Check result is shorter than original
        assert len(truncated) < len(long_content)


class TestTokenBudget:
    """Tests for TokenBudget class."""

    def test_initial_state(self):
        """Test initial budget state."""
        budget = TokenBudget(1000)
        assert budget.remaining() == 1000
        assert budget.is_over_budget() is False

    def test_use_tokens(self):
        """Test using tokens."""
        budget = TokenBudget(1000)
        assert budget.use(500) is True
        assert budget.remaining() == 500
        assert budget.used == 500

    def test_over_budget(self):
        """Test going over budget."""
        budget = TokenBudget(100)
        budget.use(150)
        assert budget.is_over_budget() is True
        assert budget.remaining() == 0

    def test_reset(self):
        """Test resetting budget."""
        budget = TokenBudget(1000)
        budget.use(500)
        budget.reset()
        assert budget.used == 0
        assert budget.remaining() == 1000

    def test_str(self):
        """Test string representation."""
        budget = TokenBudget(1000)
        budget.use(250)
        assert "250" in str(budget)
        assert "1000" in str(budget)
