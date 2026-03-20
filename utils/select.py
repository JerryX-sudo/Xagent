"""Interactive selection utilities for Xagent."""

import os
import sys
import tty
import termios
import fcntl
from dataclasses import dataclass
from typing import Callable

from rich.console import Console
from rich.text import Text
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
            # Check if more chars available
            old_flags = fcntl.fcntl(fd, fcntl.F_GETFL)
            fcntl.fcntl(fd, fcntl.F_SETFL, old_flags | os.O_NONBLOCK)
            try:
                ch2 = sys.stdin.read(1)
            except (IOError, BlockingIOError):
                ch2 = None
            finally:
                fcntl.fcntl(fd, fcntl.F_SETFL, old_flags)

            if ch2 == '[':
                ch3 = sys.stdin.read(1)
                if ch3 == 'A':
                    return 'up'
                elif ch3 == 'B':
                    return 'down'
            elif ch2 is None or ch2 == '':
                return 'esc'
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
    num_options = len(options)

    def render():
        """Render the selection menu."""
        # Move cursor up to redraw (clear previous render)
        sys.stdout.write(f'\033[{num_options + 2}A')  # Move up
        sys.stdout.write('\033[J')  # Clear from cursor to end
        sys.stdout.flush()

        console.print(f"[bold yellow]{title}[/bold yellow]")
        for i, opt in enumerate(options):
            if i == selected_idx:
                console.print(f"  [bold cyan]› {opt.label}[/bold cyan] [dim]- {opt.description}[/dim]")
            else:
                console.print(f"    {opt.label} [dim]- {opt.description}[/dim]")
        console.print("  [dim]↑↓ select | Enter confirm | Esc cancel[/dim]")

    # Initial render
    console.print(f"[bold yellow]{title}[/bold yellow]")
    for i, opt in enumerate(options):
        if i == selected_idx:
            console.print(f"  [bold cyan]› {opt.label}[/bold cyan] [dim]- {opt.description}[/dim]")
        else:
            console.print(f"    {opt.label} [dim]- {opt.description}[/dim]")
    console.print("  [dim]↑↓ select | Enter confirm | Esc cancel[/dim]")

    # Wait for key
    while True:
        key = read_key()

        if key == 'esc':
            console.print("[dim]Cancelled[/dim]")
            return None
        elif key == 'up':
            selected_idx = (selected_idx - 1) % num_options
            render()
        elif key == 'down':
            selected_idx = (selected_idx + 1) % num_options
            render()
        elif key == '\r' or key == '\n':  # Enter
            console.print(f"[cyan]→ {options[selected_idx].label}[/cyan]")
            return options[selected_idx]
        else:
            # Check shortcuts
            for i, opt in enumerate(options):
                if opt.shortcut and opt.shortcut.lower() == key.lower():
                    console.print(f"[cyan]→ {opt.label}[/cyan]")
                    return opt

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
