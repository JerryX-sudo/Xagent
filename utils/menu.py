"""Interactive menu system for Xagent."""

import os
import sys
import tty
import termios
import fcntl
from dataclasses import dataclass
from typing import Callable

from rich.console import Console


@dataclass
class MenuItem:
    """A menu item."""
    name: str
    description: str
    shortcut: str = ""
    action: Callable | None = None
    submenu: list["MenuItem"] | None = None


def read_key() -> str:
    """Read a single keypress."""
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        ch = sys.stdin.read(1)
        if ch == '\x1b':
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


def show_menu(
    items: list[MenuItem],
    title: str = "Commands",
    console: Console | None = None,
) -> MenuItem | None:
    """Show interactive menu with arrow key navigation.

    Returns selected item or None if cancelled.
    """
    if console is None:
        console = Console()

    selected_idx = 0
    num_items = len(items)

    def render():
        """Render the menu."""
        # Move cursor up and clear
        sys.stdout.write(f'\033[{num_items + 2}A')
        sys.stdout.write('\033[J')
        sys.stdout.flush()

        console.print(f"[bold cyan]{title}[/bold cyan]")
        for i, item in enumerate(items):
            prefix = "›" if i == selected_idx else " "
            if i == selected_idx:
                console.print(f"  [bold cyan]{prefix} /{item.name}[/bold cyan] [dim]- {item.description}[/dim]")
            else:
                console.print(f"  [dim]{prefix} /{item.name} - {item.description}[/dim]")
        console.print("  [dim]↑↓ select | Enter confirm | Esc cancel[/dim]")

    # Initial render
    console.print(f"[bold cyan]{title}[/bold cyan]")
    for i, item in enumerate(items):
        prefix = "›" if i == selected_idx else " "
        if i == selected_idx:
            console.print(f"  [bold cyan]{prefix} /{item.name}[/bold cyan] [dim]- {item.description}[/dim]")
        else:
            console.print(f"  [dim]{prefix} /{item.name} - {item.description}[/dim]")
    console.print("  [dim]↑↓ select | Enter confirm | Esc cancel[/dim]")

    while True:
        key = read_key()

        if key == 'esc':
            return None
        elif key == 'up':
            selected_idx = (selected_idx - 1) % num_items
            render()
        elif key == 'down':
            selected_idx = (selected_idx + 1) % num_items
            render()
        elif key == '\r' or key == '\n':
            console.print(f"[cyan]→ /{items[selected_idx].name}[/cyan]")
            return items[selected_idx]

    return None


def show_config_editor(
    config_items: list[tuple[str, str, str, Callable]],
    title: str = "Configuration",
    console: Console | None = None,
) -> None:
    """Show interactive config editor.

    Args:
        config_items: List of (name, description, current_value, setter_callback)
    """
    if console is None:
        console = Console()

    selected_idx = 0
    num_items = len(config_items) + 1  # +1 for "Done" option

    def render():
        """Render the config editor."""
        sys.stdout.write(f'\033[{num_items + 2}A')
        sys.stdout.write('\033[J')
        sys.stdout.flush()

        console.print(f"[bold yellow]{title}[/bold yellow]")
        for i, (name, desc, value, _) in enumerate(config_items):
            prefix = "›" if i == selected_idx else " "
            # Mask sensitive values
            display_value = "***" if "key" in name.lower() else value
            if i == selected_idx:
                console.print(f"  [bold cyan]{prefix} {name}[/bold cyan]: [green]{display_value}[/green]")
            else:
                console.print(f"  [dim]{prefix} {name}: {display_value}[/dim]")

        # Done option
        done_prefix = "›" if selected_idx == len(config_items) else " "
        if selected_idx == len(config_items):
            console.print(f"  [bold green]{done_prefix} Done[/bold green]")
        else:
            console.print(f"  [dim]{done_prefix} Done[/dim]")

        console.print("  [dim]↑↓ select | Enter edit | Esc cancel[/dim]")

    # Initial render
    console.print(f"[bold yellow]{title}[/bold yellow]")
    for i, (name, desc, value, _) in enumerate(config_items):
        prefix = "›" if i == selected_idx else " "
        display_value = "***" if "key" in name.lower() else value
        if i == selected_idx:
            console.print(f"  [bold cyan]{prefix} {name}[/bold cyan]: [green]{display_value}[/green]")
        else:
            console.print(f"  [dim]{prefix} {name}: {display_value}[/dim]")

    done_prefix = "›" if selected_idx == len(config_items) else " "
    if selected_idx == len(config_items):
        console.print(f"  [bold green]{done_prefix} Done[/bold green]")
    else:
        console.print(f"  [dim]{done_prefix} Done[/dim]")
    console.print("  [dim]↑↓ select | Enter edit | Esc cancel[/dim]")

    while True:
        key = read_key()

        if key == 'esc':
            console.print("[dim]Cancelled[/dim]")
            return
        elif key == 'up':
            selected_idx = (selected_idx - 1) % num_items
            render()
        elif key == 'down':
            selected_idx = (selected_idx + 1) % num_items
            render()
        elif key == '\r' or key == '\n':
            if selected_idx == len(config_items):
                # Done selected
                console.print("[green]Configuration saved[/green]")
                return
            else:
                # Edit selected item
                name, desc, current_value, setter = config_items[selected_idx]
                console.print(f"\n[cyan]Enter new value for {name}[/cyan] [dim](current: {current_value})[/dim]")
                console.print("[dim]Press Enter to keep current, or type new value:[/dim]")

                # Read new value (simple input, not raw mode)
                import sys
                termios.tcsetattr(sys.stdin.fileno(), termios.TCSADRAIN, termios.tcgetattr(sys.stdin.fileno()))
                try:
                    new_value = input("> ").strip()
                    if new_value:
                        setter(new_value)
                        config_items[selected_idx] = (name, desc, new_value, setter)
                        console.print(f"[green]✓ {name} updated[/green]")
                    else:
                        console.print("[dim]Kept current value[/dim]")
                except (KeyboardInterrupt, EOFError):
                    console.print("[dim]Cancelled[/dim]")

                # Re-render
                console.print()
                render()
