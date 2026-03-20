"""Session state management for Xagent."""

import json
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import Any

from core.config import Config


@dataclass
class Message:
    """A single message in the conversation."""

    role: str  # "user", "assistant", "system", "tool"
    content: str
    tool_calls: list[dict[str, Any]] | None = None
    tool_call_id: str | None = None
    name: str | None = None
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for API calls."""
        d: dict[str, Any] = {"role": self.role, "content": self.content}
        if self.tool_calls:
            d["tool_calls"] = self.tool_calls
        if self.tool_call_id:
            d["tool_call_id"] = self.tool_call_id
        if self.name:
            d["name"] = self.name
        return d


@dataclass
class Session:
    """Manages conversation session state."""

    messages: list[Message] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    total_tokens: int = 0
    session_id: str = field(default_factory=lambda: datetime.now().strftime("%Y%m%d_%H%M%S"))

    def add_message(
        self,
        role: str,
        content: str,
        tool_calls: list[dict[str, Any]] | None = None,
        tool_call_id: str | None = None,
        name: str | None = None,
    ) -> None:
        """Add a message to the session."""
        msg = Message(
            role=role,
            content=content,
            tool_calls=tool_calls,
            tool_call_id=tool_call_id,
            name=name,
        )
        self.messages.append(msg)

    def get_messages_for_api(self) -> list[dict[str, Any]]:
        """Get messages formatted for API calls."""
        return [msg.to_dict() for msg in self.messages]

    def clear(self) -> None:
        """Clear all messages but keep session metadata."""
        self.messages.clear()
        self.total_tokens = 0

    def save(self, name: str | None = None) -> Path:
        """Save session to file."""
        sessions_dir = Config.get_config_dir() / "sessions"
        sessions_dir.mkdir(parents=True, exist_ok=True)

        filename = name or self.session_id
        filepath = sessions_dir / f"{filename}.json"

        data = {
            "session_id": self.session_id,
            "created_at": self.created_at,
            "total_tokens": self.total_tokens,
            "messages": [asdict(msg) for msg in self.messages],
        }

        with open(filepath, "w") as f:
            json.dump(data, f, indent=2)

        return filepath

    @classmethod
    def load(cls, name: str) -> "Session":
        """Load session from file."""
        sessions_dir = Config.get_config_dir() / "sessions"
        filepath = sessions_dir / f"{name}.json"

        if not filepath.exists():
            raise FileNotFoundError(f"Session '{name}' not found")

        with open(filepath) as f:
            data = json.load(f)

        session = cls(
            created_at=data["created_at"],
            total_tokens=data["total_tokens"],
            session_id=data["session_id"],
        )

        for msg_data in data["messages"]:
            session.messages.append(Message(**msg_data))

        return session

    @classmethod
    def list_sessions(cls) -> list[str]:
        """List all saved sessions."""
        sessions_dir = Config.get_config_dir() / "sessions"
        if not sessions_dir.exists():
            return []
        return [f.stem for f in sessions_dir.glob("*.json")]
