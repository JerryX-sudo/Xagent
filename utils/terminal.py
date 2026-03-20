"""Terminal UI utilities for Xagent."""

from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich.syntax import Syntax
from rich.table import Table
from rich.live import Live
from rich.spinner import Spinner


class TerminalUI:
    """Rich-based terminal UI utilities."""

    def __init__(self):
        self.console = Console()

    def print_welcome(self) -> None:
        """Print welcome message."""
        self.console.print()
        self.console.print(
            Panel(
                "[bold cyan]Xagent[/bold cyan] - A lightweight terminal Agent\n"
                "[dim]Type your message or use /help for commands[/dim]",
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
        """Print a tool call."""
        self.console.print(f"[magenta]Calling tool:[/magenta] {name}")
        if args:
            for key, value in args.items():
                display_value = str(value)[:100]
                if len(str(value)) > 100:
                    display_value += "..."
                self.console.print(f"  [dim]{key}:[/dim] {display_value}")

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
