"""Terminal UI utilities for Xagent."""

import time
from contextlib import contextmanager
from typing import Generator

from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich.syntax import Syntax
from rich.table import Table
from rich.live import Live
from rich.spinner import Spinner
from rich.text import Text


# Tool icons mapping
TOOL_ICONS = {
    "bash": "💻",
    "edit_file": "📝",
    "read_file": "📖",
    "write_file": "📄",
    "search": "🔍",
    "glob": "🔎",
    "grep": "🔎",
    "final_answer": "✅",
    "think": "💭",
    "remember": "💾",
}


class TerminalUI:
    """Rich-based terminal UI utilities."""

    def __init__(self):
        self.console = Console()
        self._tool_start_time: float | None = None

    def print_welcome(self) -> None:
        """Print welcome message."""
        self.console.print()
        self.console.print(
            Panel(
                "[bold cyan]Xagent[/bold cyan] - A lightweight terminal Agent\n"
                "[dim]Type your message or /help for commands | ESC: stop | Ctrl+C: exit[/dim]",
                border_style="cyan",
            )
        )
        self.console.print()

    def print_message(self, role: str, content: str) -> None:
        """Print a chat message."""
        if role == "user":
            self.console.print(f"[bold green]You:[/bold green] {content}")
        elif role == "assistant":
            self.console.print(f"[bold blue]Agent:[/bold blue]")
            self.console.print(Markdown(content))
        elif role == "system":
            self.console.print(f"[dim]{content}[/dim]")
        elif role == "tool":
            self.console.print(f"[yellow]Tool Result:[/yellow] {content[:200]}...")

    def print_tool_call(self, name: str, args: dict) -> None:
        """Print a tool call (legacy, calls print_tool_start)."""
        self.print_tool_start(name, args)

    def print_tool_start(self, name: str, args: dict) -> None:
        """Print tool execution start with icon and args preview."""
        import sys
        icon = TOOL_ICONS.get(name, "🔧")
        self._tool_start_time = time.time()

        # Use direct stdout for immediate display
        sys.stdout.write("\n")
        sys.stdout.flush()
        self.console.print(f"[bold magenta]┌─ {icon} {name}[/bold magenta]")

        if args:
            for key, value in args.items():
                display_value = str(value)
                # Truncate long values
                if len(display_value) > 80:
                    display_value = display_value[:77] + "..."
                # Escape any Rich markup in values
                display_value = display_value.replace("[", "\\[")
                self.console.print(f"[magenta]│[/magenta]  [dim]{key}:[/dim] {display_value}")

        # Flush to ensure immediate display
        sys.stdout.flush()

    def print_tool_end(self, name: str, success: bool = True, message: str | None = None, elapsed: float | None = None) -> None:
        """Print tool execution end with timing and status."""
        if elapsed is None:
            elapsed = time.time() - self._tool_start_time if self._tool_start_time else 0
        self._tool_start_time = None

        if success:
            status = "[green]✓ done[/green]"
        else:
            status = "[red]✗ failed[/red]"

        msg = f"[magenta]└─[/magenta] {status} [dim]({elapsed:.2f}s)[/dim]"
        if message:
            msg += f" [dim]{message}[/dim]"
        self.console.print(msg)

    def print_error(self, message: str) -> None:
        """Print an error message."""
        self.console.print(f"[bold red]Error:[/bold red] {message}")

    def print_success(self, message: str) -> None:
        """Print a success message."""
        self.console.print(f"[bold green]{message}[/bold green]")

    def print_warning(self, message: str) -> None:
        """Print a warning message."""
        self.console.print(f"[yellow]Warning:[/yellow] {message}")

    def print_info(self, message: str) -> None:
        """Print an info message."""
        self.console.print(f"[cyan]{message}[/cyan]")

    def print_tokens(self, prompt: int, completion: int, total: int) -> None:
        """Print token usage."""
        self.console.print(
            f"[dim]Tokens: {prompt} prompt + {completion} completion = {total} total[/dim]"
        )

    def print_help(self) -> None:
        """Print help message."""
        table = Table(title="Xagent Commands", border_style="cyan")
        table.add_column("Command", style="cyan")
        table.add_column("Description")

        commands = [
            ("/help", "Show this help message"),
            ("/clear", "Clear conversation history"),
            ("/exit, /quit", "Exit Xagent"),
            ("/memory", "Show static memory"),
            ("/memory add <text>", "Add to static memory"),
            ("/memory clear", "Clear static memory"),
            ("/history", "Show conversation history"),
            ("/save [name]", "Save current session"),
            ("/load <name>", "Load a saved session"),
            ("/sessions", "List saved sessions"),
            ("/cache", "Show cache statistics"),
            ("/cache clear", "Clear request cache"),
            ("/config", "Show current configuration"),
            ("/tools", "List available tools"),
            ("/skills", "List available skills"),
            ("/permissions", "Manage tool permissions"),
            ("/permissions pause", "Pause auto-approve (ask every time)"),
            ("/permissions revoke", "Revoke all auto-approve permissions"),
            ("/export [name]", "Export conversation to markdown"),
            ("/theme [name]", "View or change color theme"),
        ]

        for cmd, desc in commands:
            table.add_row(cmd, desc)

        self.console.print(table)

    def create_spinner(self, text: str = "Thinking...") -> Live:
        """Create a spinner for async operations."""
        return Live(
            Spinner("dots", text=text, style="cyan"),
            console=self.console,
            refresh_per_second=10,
        )

    @contextmanager
    def spinner(self, text: str = "Thinking...") -> Generator[Live, None, None]:
        """Context manager for spinner display."""
        with Live(
            Spinner("dots", text=text, style="cyan"),
            console=self.console,
            refresh_per_second=10,
            transient=True,
        ) as live:
            yield live

    def print_interrupted(self) -> None:
        """Print interruption message."""
        self.console.print()
        self.console.print("[yellow]⚠ Operation interrupted[/yellow]")

    def print_code(self, code: str, language: str = "python") -> None:
        """Print syntax-highlighted code."""
        syntax = Syntax(code, language, theme="monokai", line_numbers=True)
        self.console.print(syntax)

    def print_final_answer(self, answer: str) -> None:
        """Print the final answer."""
        self.console.print()
        self.console.print(Panel(
            Markdown(answer),
            title="[bold green]Answer[/bold green]",
            border_style="green",
        ))
        self.console.print()
