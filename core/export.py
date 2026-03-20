"""Export functionality for Xagent."""

from datetime import datetime
from pathlib import Path

from core.session import Session
from core.config import Config


def export_to_markdown(session: Session, filename: str | None = None) -> Path:
    """Export session to markdown file.

    Args:
        session: Session to export
        filename: Optional filename (without extension)

    Returns:
        Path to exported file
    """
    export_dir = Config.get_config_dir() / "exports"
    export_dir.mkdir(parents=True, exist_ok=True)

    if filename is None:
        filename = f"xagent_{session.session_id}"

    filepath = export_dir / f"{filename}.md"

    lines = [
        f"# Xagent Conversation",
        f"",
        f"**Session ID:** {session.session_id}",
        f"**Created:** {session.created_at}",
        f"**Total Tokens:** {session.total_tokens}",
        f"",
        f"---",
        f"",
    ]

    for msg in session.messages:
        if msg.role == "system":
            continue  # Skip system messages

        timestamp = msg.timestamp[:19] if msg.timestamp else ""

        if msg.role == "user":
            lines.append(f"## User ({timestamp})")
            lines.append(f"")
            lines.append(msg.content)
            lines.append(f"")

        elif msg.role == "assistant":
            lines.append(f"## Assistant ({timestamp})")
            lines.append(f"")
            if msg.content:
                lines.append(msg.content)
            if msg.tool_calls:
                for tc in msg.tool_calls:
                    func = tc.get("function", {})
                    name = func.get("name", "unknown")
                    args = func.get("arguments", "{}")
                    lines.append(f"")
                    lines.append(f"**Tool Call:** `{name}`")
                    lines.append(f"```json")
                    lines.append(args)
                    lines.append(f"```")
            lines.append(f"")

        elif msg.role == "tool":
            name = msg.name or "tool"
            lines.append(f"### Tool Result: `{name}`")
            lines.append(f"")
            lines.append(f"```")
            # Truncate long outputs
            content = msg.content
            if len(content) > 2000:
                content = content[:2000] + f"\n... ({len(msg.content) - 2000} chars truncated)"
            lines.append(content)
            lines.append(f"```")
            lines.append(f"")

    lines.append(f"---")
    lines.append(f"*Exported at {datetime.now().isoformat()}*")

    filepath.write_text("\n".join(lines))
    return filepath


def export_to_json(session: Session, filename: str | None = None) -> Path:
    """Export session to JSON file.

    Args:
        session: Session to export
        filename: Optional filename (without extension)

    Returns:
        Path to exported file
    """
    export_dir = Config.get_config_dir() / "exports"
    export_dir.mkdir(parents=True, exist_ok=True)

    if filename is None:
        filename = f"xagent_{session.session_id}"

    filepath = export_dir / f"{filename}.json"

    # Use session's save method with custom path
    session.save(filename)

    # Move from sessions to exports
    sessions_file = Config.get_config_dir() / "sessions" / f"{filename}.json"
    if sessions_file.exists():
        import shutil
        shutil.move(str(sessions_file), str(filepath))

    return filepath


def list_exports() -> list[Path]:
    """List all exported files."""
    export_dir = Config.get_config_dir() / "exports"
    if not export_dir.exists():
        return []
    return list(export_dir.glob("*"))
