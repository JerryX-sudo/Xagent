"""Bash execution tool for Xagent."""

import subprocess
import shlex
import signal
import sys
import time
import threading
from typing import Any

from rich.console import Console
from rich.syntax import Syntax
from rich.panel import Panel
from rich.live import Live
from rich.spinner import Spinner
from rich.text import Text

from tools.base import BaseTool
from core.permission import PermissionManager
from utils.output import OutputManager
from utils.compat import IS_WINDOWS

if not IS_WINDOWS:
    import select


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
        self._current_process: subprocess.Popen | None = None
        self._interrupted = False

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

    def interrupt(self) -> None:
        """Interrupt the currently running command."""
        self._interrupted = True
        if self._current_process and self._current_process.poll() is None:
            try:
                self._current_process.send_signal(signal.SIGINT)
            except (ProcessLookupError, OSError):
                pass

    def is_running(self) -> bool:
        """Check if a command is currently running."""
        return self._current_process is not None and self._current_process.poll() is None

    def run(self, **kwargs: Any) -> str:
        """Execute the bash command with streaming output."""
        command = kwargs.get("command", "")
        if not command:
            return "Error: No command provided"

        # Reset interrupt flag
        self._interrupted = False

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

        start_time = time.time()
        output_lines = []
        stderr_lines = []

        try:
            # Use Popen for streaming output
            self._current_process = subprocess.Popen(
                command,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,  # Line buffered
            )

            # Print command header
            cmd_display = command if len(command) <= 60 else command[:57] + "..."
            self.console.print(f"[dim]┌─ 💻 [bold]bash:[/bold] {cmd_display}[/dim]")
            self.console.print("[dim]│[/dim]")

            # Read output in real-time
            if IS_WINDOWS:
                self._read_output_windows(output_lines, stderr_lines)
            else:
                self._read_output_unix(output_lines, stderr_lines)

            returncode = self._current_process.returncode or 0
            elapsed = time.time() - start_time

            # Print footer
            if self._interrupted:
                status = "[yellow]⚠ Interrupted[/yellow]"
            elif returncode == 0:
                status = "[green]✓ Completed[/green]"
            else:
                status = f"[red]✗ Failed (exit: {returncode})[/red]"

            self.console.print(f"[dim]└─ {status} in {elapsed:.2f}s[/dim]")

            # Build output string for agent
            output = "\n".join(output_lines)
            if stderr_lines:
                if output:
                    output += "\n"
                output += f"[stderr]\n" + "\n".join(stderr_lines)

            if returncode != 0:
                output += f"\n[exit code: {returncode}]"

            if self._interrupted:
                output += "\n[interrupted by user]"

            output = output.strip() or "(no output)"

            return output

        except subprocess.TimeoutExpired:
            if self._current_process:
                self._current_process.kill()
            return "Error: Command timed out after 120 seconds"
        except Exception as e:
            return f"Error executing command: {e}"
        finally:
            self._current_process = None

    def _read_output_windows(self, output_lines: list, stderr_lines: list) -> None:
        """Windows-specific output reading using threads."""
        import queue

        stdout_queue = queue.Queue()
        stderr_queue = queue.Queue()

        def read_stdout():
            for line in iter(self._current_process.stdout.readline, ''):
                stdout_queue.put(line.rstrip('\n'))
            stdout_queue.put(None)

        def read_stderr():
            for line in iter(self._current_process.stderr.readline, ''):
                stderr_queue.put(line.rstrip('\n'))
            stderr_queue.put(None)

        stdout_thread = threading.Thread(target=read_stdout, daemon=True)
        stderr_thread = threading.Thread(target=read_stderr, daemon=True)
        stdout_thread.start()
        stderr_thread.start()

        stdout_done = stderr_done = False

        while not (stdout_done and stderr_done):
            if self._interrupted:
                self._current_process.terminate()
                self._current_process.wait(timeout=1)
                self.console.print("[dim]|[/dim] [yellow]Interrupted by user[/yellow]")
                break

            try:
                line = stdout_queue.get_nowait()
                if line is None:
                    stdout_done = True
                else:
                    output_lines.append(line)
                    self.console.print(f"[dim]|[/dim] {line}")
            except queue.Empty:
                pass

            try:
                line = stderr_queue.get_nowait()
                if line is None:
                    stderr_done = True
                else:
                    stderr_lines.append(line)
                    self.console.print(f"[dim]|[/dim] [red]{line}[/red]")
            except queue.Empty:
                pass

            if not stdout_done or not stderr_done:
                time.sleep(0.01)

        self._current_process.wait()

    def _read_output_unix(self, output_lines: list, stderr_lines: list) -> None:
        """Unix-specific output reading using select."""
        stdout_fd = self._current_process.stdout.fileno()
        stderr_fd = self._current_process.stderr.fileno()

        while True:
            if self._interrupted:
                self._current_process.terminate()
                self._current_process.wait(timeout=1)
                self.console.print("[dim]|[/dim] [yellow]Interrupted by user[/yellow]")
                break

            if self._current_process.poll() is not None:
                remaining_stdout = self._current_process.stdout.read()
                remaining_stderr = self._current_process.stderr.read()
                if remaining_stdout:
                    for line in remaining_stdout.splitlines():
                        output_lines.append(line)
                        self.console.print(f"[dim]|[/dim] {line}")
                if remaining_stderr:
                    for line in remaining_stderr.splitlines():
                        stderr_lines.append(line)
                        self.console.print(f"[dim]|[/dim] [red]{line}[/red]")
                break

            ready, _, _ = select.select([stdout_fd, stderr_fd], [], [], 0.1)

            for fd in ready:
                if fd == stdout_fd:
                    line = self._current_process.stdout.readline()
                    if line:
                        line = line.rstrip('\n')
                        output_lines.append(line)
                        self.console.print(f"[dim]|[/dim] {line}")
                elif fd == stderr_fd:
                    line = self._current_process.stderr.readline()
                    if line:
                        line = line.rstrip('\n')
                        stderr_lines.append(line)
                        self.console.print(f"[dim]|[/dim] [red]{line}[/red]")
