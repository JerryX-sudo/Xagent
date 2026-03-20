"""Static memory for persistent storage."""

from pathlib import Path
from datetime import datetime

from core.config import Config


class StaticMemory:
    """Persistent static memory stored in ~/.xagent/memory.md."""

    def __init__(self):
        self._memory_file = Config.get_config_dir() / "memory.md"
        self._ensure_file()

    def _ensure_file(self) -> None:
        """Ensure the memory file exists."""
        if not self._memory_file.exists():
            self._memory_file.write_text("# Xagent Memory\n\n")

    def read(self) -> str:
        """Read the entire memory file."""
        self._ensure_file()
        return self._memory_file.read_text()

    def write(self, content: str) -> None:
        """Overwrite the memory file with new content."""
        self._memory_file.write_text(content)

    def append(self, content: str) -> None:
        """Append content to the memory file."""
        self._ensure_file()
        current = self._memory_file.read_text()
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        new_entry = f"\n## {timestamp}\n{content}\n"
        self._memory_file.write_text(current + new_entry)

    def search(self, query: str) -> list[str]:
        """Search for lines containing the query."""
        content = self.read()
        query_lower = query.lower()
        return [line for line in content.split("\n") if query_lower in line.lower()]

    def clear(self) -> None:
        """Clear the memory file."""
        self._memory_file.write_text("# Xagent Memory\n\n")

    def get_sections(self) -> list[tuple[str, str]]:
        """Get all sections (heading, content) from memory."""
        content = self.read()
        sections = []
        current_heading = ""
        current_content = []

        for line in content.split("\n"):
            if line.startswith("## "):
                if current_heading:
                    sections.append((current_heading, "\n".join(current_content).strip()))
                current_heading = line[3:].strip()
                current_content = []
            else:
                current_content.append(line)

        if current_heading:
            sections.append((current_heading, "\n".join(current_content).strip()))

        return sections

    def delete_section(self, heading: str) -> bool:
        """Delete a section by heading."""
        sections = self.get_sections()
        new_sections = [(h, c) for h, c in sections if h != heading]

        if len(new_sections) == len(sections):
            return False

        content = "# Xagent Memory\n\n"
        for h, c in new_sections:
            content += f"## {h}\n{c}\n\n"

        self.write(content.strip() + "\n")
        return True
