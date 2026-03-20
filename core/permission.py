"""Permission management for Xagent."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Callable

from rich.console import Console
from rich.panel import Panel

from utils.select import select_option, SelectOption


class PermissionChoice(Enum):
    """Permission choices."""
    DENY = "deny"
    ALLOW_ONCE = "allow_once"
    ALLOW_TASK = "allow_task"


@dataclass
class PermissionManager:
    """Manages permissions for tool actions."""

    # Tools that have task-level permission granted
    _task_permissions: set[str] = field(default_factory=set)
    # Whether task-level permissions are active
    _task_mode_active: bool = True
    console: Console = field(default_factory=Console)

    def request_permission(
        self,
        tool_name: str,
        action_description: str,
        details: str | None = None,
        preview_callback: Callable[[], None] | None = None,
    ) -> bool:
        """Request permission for an action.

        Args:
            tool_name: Name of the tool requesting permission
            action_description: Brief description of the action
            details: Optional detailed information
            preview_callback: Optional callback to show preview (e.g., diff)

        Returns:
            True if permission granted, False otherwise
        """
        # Check if task-level permission exists
        if self._task_mode_active and tool_name in self._task_permissions:
            self.console.print(f"[dim](auto-approved: {action_description})[/dim]")
            return True

        # Show the action details
        self.console.print()
        self.console.print(Panel(
            f"[bold]{action_description}[/bold]",
            title=f"[yellow]Permission Request: {tool_name}[/yellow]",
            border_style="yellow",
        ))

        if details:
            self.console.print(details)

        if preview_callback:
            preview_callback()

        # Interactive selection
        options = [
            SelectOption(
                label="Deny",
                value="deny",
                description="Reject this action",
                shortcut="n",
            ),
            SelectOption(
                label="Allow once",
                value="allow_once",
                description="Approve this action only",
                shortcut="y",
            ),
            SelectOption(
                label="Allow for task",
                value="allow_task",
                description="Auto-approve similar actions in this task",
                shortcut="a",
            ),
        ]

        result = select_option(options, "Choose action", self.console)

        if result is None or result.value == "deny":
            self.console.print("[red]Action denied[/red]")
            return False
        elif result.value == "allow_once":
            return True
        elif result.value == "allow_task":
            self._task_permissions.add(tool_name)
            self.console.print(f"[green]Auto-approve enabled for {tool_name}[/green]")
            return True

        return False

    def revoke_task_permission(self, tool_name: str) -> bool:
        """Revoke task-level permission for a tool."""
        if tool_name in self._task_permissions:
            self._task_permissions.discard(tool_name)
            return True
        return False

    def revoke_all_task_permissions(self) -> int:
        """Revoke all task-level permissions. Returns count revoked."""
        count = len(self._task_permissions)
        self._task_permissions.clear()
        return count

    def list_task_permissions(self) -> list[str]:
        """List all tools with task-level permission."""
        return list(self._task_permissions)

    def pause_task_mode(self) -> None:
        """Pause task-mode auto-approve (will ask again)."""
        self._task_mode_active = False

    def resume_task_mode(self) -> None:
        """Resume task-mode auto-approve."""
        self._task_mode_active = True

    def is_task_mode_active(self) -> bool:
        """Check if task mode is active."""
        return self._task_mode_active

    def reset_for_new_task(self) -> None:
        """Reset permissions for a new task."""
        self._task_permissions.clear()
        self._task_mode_active = True
