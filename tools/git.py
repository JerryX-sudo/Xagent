"""Git tools for Xagent."""

import shlex
import subprocess
from typing import Any

from tools.base import BaseTool
from core.permission import PermissionManager


class GitTool(BaseTool):
    """Tool for git operations."""

    name = "git"
    description = "Execute git commands. Common operations: status, diff, log, add, commit, branch, checkout."
    parameters = {
        "type": "object",
        "properties": {
            "command": {
                "type": "string",
                "description": "Git subcommand (e.g., 'status', 'diff', 'log')",
            },
            "args": {
                "type": "string",
                "description": "Additional arguments for the git command",
            },
        },
        "required": ["command"],
    }

    # Commands that need permission
    DANGEROUS_COMMANDS = {
        "push", "reset", "rebase", "merge", "checkout",
        "branch -d", "branch -D", "clean", "stash drop",
    }

    def __init__(self, permission_manager: PermissionManager | None = None):
        self.permission_manager = permission_manager or PermissionManager()

    def _needs_permission(self, command: str, args: str) -> bool:
        """Check if command needs permission."""
        full_cmd = f"{command} {args}".strip()
        for dangerous in self.DANGEROUS_COMMANDS:
            if full_cmd.startswith(dangerous):
                return True
        return False

    def run(self, **kwargs: Any) -> str:
        """Execute git command."""
        command = kwargs.get("command", "")
        args = kwargs.get("args", "")

        if not command:
            return "Error: command required"

        # Build full command
        full_args = f"{command} {args}".strip()

        # Check permission for dangerous commands
        if self._needs_permission(command, args):
            if not self.permission_manager.request_permission(
                tool_name="git",
                action_description=f"Execute: git {full_args}",
            ):
                return "Git command cancelled by user"

        try:
            result = subprocess.run(
                ["git"] + shlex.split(full_args),
                capture_output=True,
                encoding="utf-8",
                errors="replace",
                timeout=30,
            )

            output = ""
            if result.stdout:
                output += result.stdout
            if result.stderr:
                if output:
                    output += "\n"
                output += result.stderr

            if result.returncode != 0:
                output += f"\n[exit code: {result.returncode}]"

            return output.strip() or "(no output)"

        except subprocess.TimeoutExpired:
            return "Error: Git command timed out"
        except FileNotFoundError:
            return "Error: Git not found. Is git installed?"
        except Exception as e:
            return f"Error: {e}"


class GitStatusTool(BaseTool):
    """Quick tool for git status."""

    name = "git_status"
    description = "Show git repository status (changed files, branch, etc.)"
    parameters = {
        "type": "object",
        "properties": {},
    }

    def run(self, **kwargs: Any) -> str:
        """Get git status."""
        try:
            result = subprocess.run(
                ["git", "status", "-sb"],
                capture_output=True,
                encoding="utf-8",
                errors="replace",
                timeout=10,
            )
            return result.stdout.strip() or result.stderr.strip() or "(no output)"
        except Exception as e:
            return f"Error: {e}"


class GitDiffTool(BaseTool):
    """Tool for viewing git diffs."""

    name = "git_diff"
    description = "Show git diff. Can diff working tree, staged changes, or between commits."
    parameters = {
        "type": "object",
        "properties": {
            "staged": {
                "type": "boolean",
                "description": "Show staged changes (--cached)",
            },
            "file": {
                "type": "string",
                "description": "Specific file to diff",
            },
            "commit": {
                "type": "string",
                "description": "Commit or range to diff (e.g., 'HEAD~3', 'main..feature')",
            },
        },
    }

    def run(self, **kwargs: Any) -> str:
        """Get git diff."""
        staged = kwargs.get("staged", False)
        file = kwargs.get("file", "")
        commit = kwargs.get("commit", "")

        cmd = ["git", "diff"]

        if staged:
            cmd.append("--cached")
        if commit:
            cmd.append(commit)
        if file:
            cmd.extend(["--", file])

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                encoding="utf-8",
                errors="replace",
                timeout=30,
            )

            output = result.stdout.strip()
            if not output:
                return "No changes"

            # Truncate if too long
            if len(output) > 5000:
                output = output[:5000] + f"\n... (truncated, showing first 5000 chars)"

            return output

        except Exception as e:
            return f"Error: {e}"


class GitLogTool(BaseTool):
    """Tool for viewing git log."""

    name = "git_log"
    description = "Show git commit history."
    parameters = {
        "type": "object",
        "properties": {
            "count": {
                "type": "integer",
                "description": "Number of commits to show (default: 10)",
            },
            "oneline": {
                "type": "boolean",
                "description": "Show one line per commit (default: true)",
            },
            "file": {
                "type": "string",
                "description": "Show history for specific file",
            },
        },
    }

    def run(self, **kwargs: Any) -> str:
        """Get git log."""
        count = kwargs.get("count", 10)
        oneline = kwargs.get("oneline", True)
        file = kwargs.get("file", "")

        cmd = ["git", "log", f"-{count}"]

        if oneline:
            cmd.append("--oneline")
        else:
            cmd.append("--format=%h %ad %s (%an)")
            cmd.append("--date=short")

        if file:
            cmd.extend(["--", file])

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                encoding="utf-8",
                errors="replace",
                timeout=10,
            )
            return result.stdout.strip() or "No commits"
        except Exception as e:
            return f"Error: {e}"
