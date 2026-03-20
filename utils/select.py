"""Interactive selection utilities for Xagent."""

import sys
import tty
import termios
from dataclasses import dataclass
from typing import Callable

from rich.console import Console
from rich.text import Text
from rich.live import Live
from rich.panel import Panel


@dataclass
class SelectOption:
    """An option in a selection menu."""
    label: str
    value: str
    description: str = ""
    shortcut: str = ""


def read_key() -> str:
    """Read a single keypress."""
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        ch = sys.stdin.read(1)
        if ch == '\x1b':  # Escape sequence
            ch2 = sys.stdin.read(1)
            if ch2 == '[':
                ch3 = sys.stdin.read(1)
                if ch3 == 'A':
                    return 'up'
                elif ch3 == 'B':
                    return 'down'
        return ch
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)


def select_option(
    options: list[SelectOption],
    title: str = "Select an option",
    console: Console | None = None,
) -> SelectOption | None:
    """Interactive selection with arrow keys.

    Args:
        options: List of options to choose from
        title: Title to display
        console: Rich console instance

    Returns:
        Selected option or None if cancelled
    """
    if console is None:
        console = Console()

    selected_idx = 0

    def render() -> Panel:
        text = Text()
        for i, opt in enumerate(options):
            prefix = "› " if i == selected_idx else "  "
            style = "bold cyan" if i == selected_idx else "dim"

            # Option line
            text.append(prefix, style=style)
            text.append(opt.label, style=style)

            # Shortcut hint
            if opt.shortcut:
                text.append(f" [{opt.shortcut}]", style="dim yellow")

            text.append("\n")

            # Description
            if opt.description and i == selected_idx:
                text.append(f"    {opt.description}\n", style="dim italic")

        # Help text
        text.append("\n")
        text.append("↑/↓ navigate  ", style="dim")
        text.append("Enter select  ", style="dim")
        text.append("Esc cancel", style="dim")

        return Panel(text, title=f"[bold]{title}[/bold]", border_style="yellow")

    with Live(render(), console=console, refresh_per_second=30, transient=True) as live:
        while True:
            key = read_key()

            if key == 'up':
                selected_idx = (selected_idx - 1) % len(options)
            elif key == 'down':
                selected_idx = (selected_idx + 1) % len(options)
            elif key == '\r' or key == '\n':  # Enter
                live.stop()
                console.print(f"[cyan]Selected:[/cyan] {options[selected_idx].label}")
                return options[selected_idx]
            elif key == '\x1b' or key == 'q':  # Escape or q
                live.stop()
                console.print("[dim]Cancelled[/dim]")
                return None
            # Check shortcuts
            else:
                for i, opt in enumerate(options):
                    if opt.shortcut.lower() == key.lower():
                        live.stop()
                        console.print(f"[cyan]Selected:[/cyan] {opt.label}")
                        return opt

            live.update(render())

    return None


def confirm(
    message: str,
    default: bool = False,
    console: Console | None = None,
) -> bool:
    """Quick yes/no confirmation.

    Args:
        message: Question to ask
        default: Default value if Enter pressed
        console: Rich console instance

    Returns:
        True if confirmed, False otherwise
    """
    if console is None:
        console = Console()

    options = [
        SelectOption("Yes", "yes", "Confirm this action", "y"),
        SelectOption("No", "no", "Cancel this action", "n"),
    ]

    if not default:
        options = list(reversed(options))

    result = select_option(options, message, console)
    return result is not None and result.value == "yes"
