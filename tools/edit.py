"""File editing tool for Xagent."""

import os
from pathlib import Path
from typing import Any

from rich.console import Console

from tools.base import BaseTool
from core.permission import PermissionManager
from utils.diff import print_inline_diff


class EditTool(BaseTool):
    """Tool for editing files with diff preview and permission control."""

    name = "edit"
    description = "Edit a file by replacing text. Shows diff preview and asks for permission before applying changes."
    parameters = {
        "type": "object",
        "properties": {
            "file_path": {
                "type": "string",
                "description": "Path to the file to edit",
            },
            "old_text": {
                "type": "string",
                "description": "The exact text to find and replace (must be unique in the file)",
            },
            "new_text": {
                "type": "string",
                "description": "The text to replace it with",
            },
        },
        "required": ["file_path", "old_text", "new_text"],
    }

    def __init__(self, permission_manager: PermissionManager):
        self.permission_manager = permission_manager
        self.console = Console()

    def run(self, **kwargs: Any) -> str:
        """Edit a file with permission check."""
        file_path = kwargs.get("file_path", "")
        old_text = kwargs.get("old_text", "")
        new_text = kwargs.get("new_text", "")

        if not file_path:
            return "Error: file_path required"
        if not old_text:
            return "Error: old_text required"
        if old_text == new_text:
            return "Error: old_text and new_text are the same"

        path = Path(file_path).expanduser().resolve()

        # Check file exists
        if not path.exists():
            return f"Error: File not found: {path}"

        # Read current content
        try:
            content = path.read_text()
        except Exception as e:
            return f"Error reading file: {e}"

        # Check old_text exists and is unique
        count = content.count(old_text)
        if count == 0:
            return f"Error: old_text not found in file"
        if count > 1:
            return f"Error: old_text found {count} times, must be unique. Provide more context."

        # Generate new content
        new_content = content.replace(old_text, new_text, 1)

        # Request permission with diff preview
        def show_preview():
            print_inline_diff(content, new_content, path.name, self.console)

        action_desc = f"Edit file: {path.name}"
        details = f"File: {path}\nReplacing {len(old_text)} chars with {len(new_text)} chars"

        if not self.permission_manager.request_permission(
            tool_name="edit",
            action_description=action_desc,
            details=details,
            preview_callback=show_preview,
        ):
            return "Edit cancelled by user"

        # Apply the edit
        try:
            path.write_text(new_content)
            return f"Successfully edited {path.name}"
        except Exception as e:
            return f"Error writing file: {e}"


class WriteFileTool(BaseTool):
    """Tool for creating or overwriting files."""

    name = "write_file"
    description = "Create a new file or overwrite an existing file. Shows diff for existing files."
    parameters = {
        "type": "object",
        "properties": {
            "file_path": {
                "type": "string",
                "description": "Path to the file to create/write",
            },
            "content": {
                "type": "string",
                "description": "Content to write to the file",
            },
        },
        "required": ["file_path", "content"],
    }

    def __init__(self, permission_manager: PermissionManager):
        self.permission_manager = permission_manager
        self.console = Console()

    def run(self, **kwargs: Any) -> str:
        """Write a file with permission check."""
        file_path = kwargs.get("file_path", "")
        content = kwargs.get("content", "")

        if not file_path:
            return "Error: file_path required"

        path = Path(file_path).expanduser().resolve()

        # Get old content if file exists
        old_content = ""
        is_new = not path.exists()

        if not is_new:
            try:
                old_content = path.read_text()
            except Exception as e:
                return f"Error reading existing file: {e}"

        # Request permission
        def show_preview():
            if is_new:
                self.console.print(f"[green]Creating new file with {len(content)} chars[/green]")
                # Show first few lines
                lines = content.split('\n')[:10]
                for i, line in enumerate(lines, 1):
                    self.console.print(f"[green]+ {i:4d} │ {line}[/green]")
                if len(content.split('\n')) > 10:
                    self.console.print(f"[dim]  ... and {len(content.split(chr(10))) - 10} more lines[/dim]")
            else:
                print_inline_diff(old_content, content, path.name, self.console)

        action_desc = f"{'Create' if is_new else 'Overwrite'} file: {path.name}"
        details = f"File: {path}\nSize: {len(content)} chars"

        if not self.permission_manager.request_permission(
            tool_name="write_file",
            action_description=action_desc,
            details=details,
            preview_callback=show_preview,
        ):
            return "Write cancelled by user"

        # Create parent directories if needed
        path.parent.mkdir(parents=True, exist_ok=True)

        # Write the file
        try:
            path.write_text(content)
            return f"Successfully {'created' if is_new else 'wrote'} {path.name}"
        except Exception as e:
            return f"Error writing file: {e}"


class ReadFileTool(BaseTool):
    """Tool for reading file contents."""

    name = "read_file"
    description = "Read the contents of a file."
    parameters = {
        "type": "object",
        "properties": {
            "file_path": {
                "type": "string",
                "description": "Path to the file to read",
            },
            "start_line": {
                "type": "integer",
                "description": "Starting line number (1-indexed, optional)",
            },
            "end_line": {
                "type": "integer",
                "description": "Ending line number (inclusive, optional)",
            },
        },
        "required": ["file_path"],
    }

    def run(self, **kwargs: Any) -> str:
        """Read a file."""
        file_path = kwargs.get("file_path", "")
        start_line = kwargs.get("start_line")
        end_line = kwargs.get("end_line")

        if not file_path:
            return "Error: file_path required"

        path = Path(file_path).expanduser().resolve()

        if not path.exists():
            return f"Error: File not found: {path}"

        try:
            content = path.read_text()
        except Exception as e:
            return f"Error reading file: {e}"

        lines = content.split('\n')

        # Handle line range
        if start_line is not None or end_line is not None:
            start = (start_line or 1) - 1  # Convert to 0-indexed
            end = end_line or len(lines)
            lines = lines[start:end]
            # Add line numbers
            numbered = []
            for i, line in enumerate(lines, start=start + 1):
                numbered.append(f"{i:4d} │ {line}")
            return '\n'.join(numbered)

        return content
