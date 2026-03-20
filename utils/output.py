"""Collapsible output display for Xagent."""

import sys
import tty
import termios
from dataclasses import dataclass, field
from typing import Callable

from rich.console import Console
from rich.text import Text
from rich.panel import Panel
from rich.live import Live


@dataclass
class CollapsibleOutput:
    """A collapsible output section."""

    title: str
    content: str
    expanded: bool = False
    preview_lines: int = 3
    exit_code: int | None = None

    def get_preview(self) -> str:
        """Get preview (first few lines)."""
        lines = self.content.strip().split('\n')
        if len(lines) <= self.preview_lines:
            return self.content.strip()
        preview = '\n'.join(lines[:self.preview_lines])
        remaining = len(lines) - self.preview_lines
        return f"{preview}\n... ({remaining} more lines)"


class OutputManager:
    """Manages collapsible outputs in the terminal."""

    def __init__(self, console: Console | None = None):
        self.console = console or Console()
        self.outputs: list[CollapsibleOutput] = []
        self._watching = False

    def add_output(
        self,
        title: str,
        content: str,
        exit_code: int | None = None,
        auto_expand_on_error: bool = True,
    ) -> CollapsibleOutput:
        """Add a collapsible output.

        Args:
            title: Title of the output section
            content: Full output content
            exit_code: Optional exit code (for commands)
            auto_expand_on_error: Expand automatically if exit code != 0
        """
        expanded = auto_expand_on_error and exit_code is not None and exit_code != 0
        output = CollapsibleOutput(
            title=title,
            content=content,
            expanded=expanded,
            exit_code=exit_code,
        )
        self.outputs.append(output)
        return output

    def render_output(self, output: CollapsibleOutput, index: int) -> Panel:
        """Render a single output section."""
        # Status indicator
        if output.exit_code is not None:
            if output.exit_code == 0:
                status = "[green]✓[/green]"
            else:
                status = f"[red]✗ exit:{output.exit_code}[/red]"
        else:
            status = ""

        # Expand/collapse indicator
        expand_icon = "▼" if output.expanded else "▶"
        shortcut = f"[dim][{index + 1}][/dim]"

        title = f"{expand_icon} {shortcut} {output.title} {status}"

        if output.expanded:
            content = output.content
            border_style = "blue"
        else:
            content = Text(output.get_preview(), style="dim")
            border_style = "dim"

        return Panel(
            content,
            title=title,
            border_style=border_style,
            subtitle="[dim]Press number to toggle[/dim]" if not output.expanded else None,
        )

    def display_output(
        self,
        title: str,
        content: str,
        exit_code: int | None = None,
    ) -> str:
        """Display output with collapse/expand option.

        Returns the content (for agent to read).
        """
        output = self.add_output(title, content, exit_code)
        index = len(self.outputs) - 1

        # Show collapsed by default (unless error)
        panel = self.render_output(output, index)
        self.console.print(panel)

        # Show hint
        self.console.print(
            f"[dim]Press [bold]{index + 1}[/bold] to {'collapse' if output.expanded else 'expand'} "
            f"| [bold]o[/bold] toggle all | [bold]Enter[/bold] continue[/dim]"
        )

        return content

    def show_interactive(self, timeout: float = 0.5) -> None:
        """Show interactive view for all outputs.

        User can toggle expand/collapse with number keys.
        """
        if not self.outputs:
            return

        def render_all() -> Text:
            text = Text()
            for i, output in enumerate(self.outputs):
                panel = self.render_output(output, i)
                # Can't nest panels in Text, so render inline
                icon = "▼" if output.expanded else "▶"
                status = ""
                if output.exit_code is not None:
                    status = " ✓" if output.exit_code == 0 else f" ✗({output.exit_code})"

                text.append(f"{icon} [{i+1}] {output.title}{status}\n",
                           style="bold cyan" if output.expanded else "dim")

                if output.expanded:
                    for line in output.content.split('\n'):
                        text.append(f"  {line}\n")
                else:
                    preview = output.get_preview()
                    for line in preview.split('\n')[:2]:
                        text.append(f"  {line}\n", style="dim")

            text.append("\n")
            text.append("[1-9] toggle  ", style="dim")
            text.append("[o] toggle all  ", style="dim")
            text.append("[Enter] continue", style="dim")
            return text

        # Non-blocking check for input
        import select as sel

        self.console.print(render_all())

        # Quick check for user input (non-blocking)
        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)

        try:
            tty.setraw(fd)

            while True:
                # Check if input available (with timeout)
                ready, _, _ = sel.select([sys.stdin], [], [], timeout)
                if not ready:
                    break  # No input, continue

                ch = sys.stdin.read(1)

                if ch == '\r' or ch == '\n':
                    break
                elif ch == 'o':
                    # Toggle all
                    all_expanded = all(o.expanded for o in self.outputs)
                    for o in self.outputs:
                        o.expanded = not all_expanded
                    self.console.clear()
                    self.console.print(render_all())
                elif ch.isdigit():
                    idx = int(ch) - 1
                    if 0 <= idx < len(self.outputs):
                        self.outputs[idx].expanded = not self.outputs[idx].expanded
                        self.console.clear()
                        self.console.print(render_all())
                elif ch == '\x1b' or ch == 'q':
                    break

        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)

    def clear(self) -> None:
        """Clear all stored outputs."""
        self.outputs.clear()
