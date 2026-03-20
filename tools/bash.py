"""Bash execution tool for Xagent."""

import subprocess
import shlex
from typing import Any

from rich.console import Console
from rich.syntax import Syntax
from rich.panel import Panel

from tools.base import BaseTool
from core.permission import PermissionManager
from utils.output import OutputManager


class BashTool(BaseTool):
    """Tool for executing bash commands."""

    name = "bash"
    description = "Execute a bash command in the terminal. Use this to run shell commands, scripts, or interact with the system."
    parameters = {
        "type": "object",
        "properties": {
            "command": {
                "type": "string",
                "description": "The bash command to execute",
            },
        },
        "required": ["command"],
    }

    # Commands that would cause recursive calls
    FORBIDDEN_COMMANDS = ["xagent", "python -m xagent", "python3 -m xagent"]

    def __init__(
        self,
        dangerous_commands: list[str] | None = None,
        permission_manager: PermissionManager | None = None,
        output_manager: OutputManager | None = None,
    ):
        self.dangerous_commands = dangerous_commands or [
            "rm", "sudo", "chmod", "chown", "dd", "mkfs", "kill", "pkill",
            "killall", "reboot", "shutdown", "poweroff", "halt", "init",
        ]
        self.permission_manager = permission_manager or PermissionManager()
        self.output_manager = output_manager
        self.console = Console()

    def _is_forbidden(self, command: str) -> bool:
        """Check if command would cause recursive xagent call."""
        cmd_lower = command.lower().strip()
        for forbidden in self.FORBIDDEN_COMMANDS:
            if cmd_lower.startswith(forbidden) or f" {forbidden}" in cmd_lower:
                return True
            # Also check for pipes/chains
            for part in cmd_lower.replace("&&", "|").replace(";", "|").split("|"):
                part = part.strip()
                if part.startswith(forbidden):
                    return True
        return False

    def _is_dangerous(self, command: str) -> bool:
        """Check if command contains dangerous operations."""
        try:
            cmd_parts = shlex.split(command)
        except ValueError:
            return True  # Malformed command, treat as dangerous

        if not cmd_parts:
            return False

        base_cmd = cmd_parts[0].split("/")[-1]
        if base_cmd in self.dangerous_commands:
            return True

        for part in command.split("|"):
            part = part.strip()
            if part:
                first_word = part.split()[0].split("/")[-1]
                if first_word in self.dangerous_commands:
                    return True

        return False

    def run(self, **kwargs: Any) -> str:
        """Execute the bash command."""
        command = kwargs.get("command", "")
        if not command:
            return "Error: No command provided"

        # Block recursive xagent calls
        if self._is_forbidden(command):
            return "Error: Cannot execute xagent from within xagent (recursive call forbidden)"

        # Check for dangerous commands and request permission
        if self._is_dangerous(command):
            def show_preview():
                self.console.print(Panel(
                    Syntax(command, "bash", theme="monokai"),
                    title="[red]Dangerous Command[/red]",
                    border_style="red",
                ))

            if not self.permission_manager.request_permission(
                tool_name="bash",
                action_description=f"Execute dangerous command",
                details=f"Command: {command}",
                preview_callback=show_preview,
            ):
                return "Command execution cancelled by user"

        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=120,
            )

            output = ""
            if result.stdout:
                output += result.stdout
            if result.stderr:
                if output:
                    output += "\n"
                output += f"[stderr]\n{result.stderr}"

            if result.returncode != 0:
                output += f"\n[exit code: {result.returncode}]"

            output = output.strip() or "(no output)"

            # Display with collapsible output if manager available
            if self.output_manager:
                # Truncate command for title if too long
                title = command if len(command) <= 50 else command[:47] + "..."
                self.output_manager.display_output(
                    title=f"$ {title}",
                    content=output,
                    exit_code=result.returncode,
                )

            return output

        except subprocess.TimeoutExpired:
            return "Error: Command timed out after 120 seconds"
        except Exception as e:
            return f"Error executing command: {e}"
