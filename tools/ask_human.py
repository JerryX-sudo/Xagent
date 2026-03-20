"""Human interaction tool for Xagent."""

from typing import Any

from rich.console import Console
from rich.prompt import Prompt
from rich.panel import Panel

from tools.base import BaseTool


class AskHumanTool(BaseTool):
    """Tool for asking questions to the human user."""

    name = "ask_human"
    description = "Ask the human user a question when you need clarification or additional information."
    parameters = {
        "type": "object",
        "properties": {
            "question": {
                "type": "string",
                "description": "The question to ask the user",
            },
            "options": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Optional list of suggested options for the user to choose from",
            },
        },
        "required": ["question"],
    }

    def __init__(self):
        self.console = Console()

    def run(self, **kwargs: Any) -> str:
        """Ask the user a question and return their response."""
        question = kwargs.get("question", "")
        options = kwargs.get("options", [])

        if not question:
            return "Error: No question provided"

        self.console.print()
        self.console.print(Panel(question, title="[bold cyan]Agent Question[/bold cyan]", border_style="cyan"))

        if options:
            self.console.print("[dim]Suggested options:[/dim]")
            for i, opt in enumerate(options, 1):
                self.console.print(f"  [cyan]{i}.[/cyan] {opt}")
            self.console.print()

            response = Prompt.ask("Your answer (number or custom text)")

            if response.isdigit():
                idx = int(response) - 1
                if 0 <= idx < len(options):
                    return options[idx]

            return response
        else:
            response = Prompt.ask("Your answer")
            return response
