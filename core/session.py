"""Session state management for Xagent."""

import json
from datetime import datetime, timedelta
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import Any

from core.config import Config

SESSION_EXPIRY_DAYS = 7
MAX_RESUMABLE_SESSIONS = 3


@dataclass
class Message:
    """A single message in the conversation."""

    role: str  # "user", "assistant", "system", "tool"
    content: str
    thinking: str | None = None
    thinking_signature: str | None = None
    tool_calls: list[dict[str, Any]] | None = None
    tool_call_id: str | None = None
    name: str | None = None
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self, reasoning_enabled: bool = True) -> dict[str, Any]:
        """Convert to dictionary for API calls."""
        d: dict[str, Any] = {"role": self.role, "content": self.content}
        if self.thinking is not None:
            # reasoning_content must always be sent back (DeepSeek reasoner requirement)
            d["reasoning_content"] = self.thinking
            if reasoning_enabled:
                d["thinking"] = self.thinking
        if self.thinking_signature is not None:
            if reasoning_enabled:
                d["thinking_signature"] = self.thinking_signature
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
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    total_tokens: int = 0
    session_id: str = field(default_factory=lambda: datetime.now().strftime("%Y%m%d_%H%M%S"))
    title: str = ""  # Auto-generated from first user message

    def add_message(
        self,
        role: str,
        content: str,
        thinking: str | None = None,
        thinking_signature: str | None = None,
        tool_calls: list[dict[str, Any]] | None = None,
        tool_call_id: str | None = None,
        name: str | None = None,
    ) -> None:
        """Add a message to the session."""
        msg = Message(
            role=role,
            content=content,
            thinking=thinking,
            thinking_signature=thinking_signature,
            tool_calls=tool_calls,
            tool_call_id=tool_call_id,
            name=name,
        )
        self.messages.append(msg)
        self.updated_at = datetime.now().isoformat()

        # Auto-generate title from first user message
        if not self.title and role == "user" and content:
            self.title = content[:50] + ("..." if len(content) > 50 else "")

    def get_messages_for_api(self, reasoning_enabled: bool = True) -> list[dict[str, Any]]:
        """Get messages formatted for API calls."""
        return [msg.to_dict(reasoning_enabled=reasoning_enabled) for msg in self.messages]

    def clear(self) -> None:
        """Clear all messages but keep session metadata."""
        self.messages.clear()
        self.total_tokens = 0

    def save(self, name: str | None = None, auto: bool = False) -> Path:
        """Save session to file.

        Args:
            name: Optional custom name for the session file
            auto: If True, save to auto-save directory for /resume
        """
        if auto:
            sessions_dir = Config.get_config_dir() / "sessions" / "auto"
        else:
            sessions_dir = Config.get_config_dir() / "sessions"
        sessions_dir.mkdir(parents=True, exist_ok=True)

        filename = name or self.session_id
        filepath = sessions_dir / f"{filename}.json"

        self.updated_at = datetime.now().isoformat()

        data = {
            "session_id": self.session_id,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "total_tokens": self.total_tokens,
            "title": self.title,
            "messages": [asdict(msg) for msg in self.messages],
        }

        with open(filepath, "w") as f:
            json.dump(data, f, indent=2)

        return filepath

    @classmethod
    def load(cls, name: str, auto: bool = False) -> "Session":
        """Load session from file."""
        if auto:
            sessions_dir = Config.get_config_dir() / "sessions" / "auto"
        else:
            sessions_dir = Config.get_config_dir() / "sessions"
        filepath = sessions_dir / f"{name}.json"

        if not filepath.exists():
            raise FileNotFoundError(f"Session '{name}' not found")

        with open(filepath) as f:
            data = json.load(f)

        session = cls(
            created_at=data["created_at"],
            updated_at=data.get("updated_at", data["created_at"]),
            total_tokens=data["total_tokens"],
            session_id=data["session_id"],
            title=data.get("title", ""),
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

    @classmethod
    def list_resumable_sessions(cls) -> list[dict[str, Any]]:
        """List auto-saved sessions that can be resumed.

        Returns sessions sorted by updated_at (newest first), limited to MAX_RESUMABLE_SESSIONS.
        Automatically cleans up expired sessions.
        """
        sessions_dir = Config.get_config_dir() / "sessions" / "auto"
        if not sessions_dir.exists():
            return []

        sessions = []
        now = datetime.now()
        expiry_threshold = now - timedelta(days=SESSION_EXPIRY_DAYS)

        for filepath in sessions_dir.glob("*.json"):
            try:
                with open(filepath) as f:
                    data = json.load(f)

                updated_at = datetime.fromisoformat(data.get("updated_at", data["created_at"]))

                # Check if expired
                if updated_at < expiry_threshold:
                    filepath.unlink()  # Delete expired session
                    continue

                sessions.append({
                    "session_id": data["session_id"],
                    "title": data.get("title", "(no title)"),
                    "updated_at": data.get("updated_at", data["created_at"]),
                    "message_count": len(data.get("messages", [])),
                })
            except (json.JSONDecodeError, KeyError):
                continue

        # Sort by updated_at descending
        sessions.sort(key=lambda x: x["updated_at"], reverse=True)

        # Keep only MAX_RESUMABLE_SESSIONS, delete the rest
        if len(sessions) > MAX_RESUMABLE_SESSIONS:
            for old_session in sessions[MAX_RESUMABLE_SESSIONS:]:
                old_path = sessions_dir / f"{old_session['session_id']}.json"
                if old_path.exists():
                    old_path.unlink()
            sessions = sessions[:MAX_RESUMABLE_SESSIONS]

        return sessions

    @classmethod
    def delete_auto_session(cls, session_id: str) -> bool:
        """Delete an auto-saved session."""
        sessions_dir = Config.get_config_dir() / "sessions" / "auto"
        filepath = sessions_dir / f"{session_id}.json"
        if filepath.exists():
            filepath.unlink()
            return True
        return False
