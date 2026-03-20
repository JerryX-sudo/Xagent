"""Tests for session module."""

import sys
from pathlib import Path

# Ensure correct path
sys.path.insert(0, str(Path(__file__).parent.parent))

import json

import pytest

from core.session import Session, Message
from core.config import Config


class TestMessage:
    """Tests for Message class."""

    def test_message_creation(self):
        """Test creating a message."""
        msg = Message(role="user", content="Hello")
        assert msg.role == "user"
        assert msg.content == "Hello"
        assert msg.tool_calls is None
        assert msg.timestamp is not None

    def test_message_to_dict(self):
        """Test converting message to dict."""
        msg = Message(role="user", content="Hello")
        d = msg.to_dict()
        assert d["role"] == "user"
        assert d["content"] == "Hello"
        assert "tool_calls" not in d

    def test_message_with_tool_calls(self):
        """Test message with tool calls."""
        tool_calls = [{"id": "1", "function": {"name": "test"}}]
        msg = Message(role="assistant", content="", tool_calls=tool_calls)
        d = msg.to_dict()
        assert d["tool_calls"] == tool_calls


class TestSession:
    """Tests for Session class."""

    def test_session_creation(self):
        """Test creating a session."""
        session = Session()
        assert len(session.messages) == 0
        assert session.total_tokens == 0
        assert session.session_id is not None

    def test_add_message(self):
        """Test adding messages."""
        session = Session()
        session.add_message("user", "Hello")
        session.add_message("assistant", "Hi there!")

        assert len(session.messages) == 2
        assert session.messages[0].role == "user"
        assert session.messages[1].role == "assistant"

    def test_get_messages_for_api(self):
        """Test getting messages in API format."""
        session = Session()
        session.add_message("user", "Hello")
        session.add_message("assistant", "Hi!")

        messages = session.get_messages_for_api()
        assert len(messages) == 2
        assert messages[0] == {"role": "user", "content": "Hello"}
        assert messages[1] == {"role": "assistant", "content": "Hi!"}

    def test_clear(self):
        """Test clearing session."""
        session = Session()
        session.add_message("user", "Hello")
        session.total_tokens = 100

        session.clear()
        assert len(session.messages) == 0
        assert session.total_tokens == 0

    def test_save_and_load(self, tmp_path, monkeypatch):
        """Test saving and loading session."""
        monkeypatch.setattr(Config, "get_config_dir", lambda: tmp_path)

        session = Session()
        session.add_message("user", "Test message")
        session.total_tokens = 50

        path = session.save("test_session")
        assert path.exists()

        loaded = Session.load("test_session")
        assert len(loaded.messages) == 1
        assert loaded.messages[0].content == "Test message"
        assert loaded.total_tokens == 50

    def test_list_sessions(self, tmp_path, monkeypatch):
        """Test listing sessions."""
        monkeypatch.setattr(Config, "get_config_dir", lambda: tmp_path)

        session1 = Session()
        session1.save("session1")

        session2 = Session()
        session2.save("session2")

        sessions = Session.list_sessions()
        assert "session1" in sessions
        assert "session2" in sessions
