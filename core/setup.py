"""First-time setup wizard for Xagent."""

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt, Confirm

from core.config import Config
from utils.select import select_option, SelectOption


def run_setup_wizard(console: Console | None = None) -> Config:
    """Run interactive setup wizard.

    Returns configured Config object.
    """
    if console is None:
        console = Console()

    console.print()
    console.print(Panel(
        "[bold cyan]Welcome to Xagent![/bold cyan]\n\n"
        "Let's set up your configuration.",
        border_style="cyan",
    ))
    console.print()

    config = Config()

    # Select model type
    model_options = [
        SelectOption(
            "OpenAI",
            "openai",
            "GPT-4o, GPT-4, etc. (Recommended)",
            "1",
        ),
        SelectOption(
            "Anthropic",
            "anthropic",
            "Claude models",
            "2",
        ),
        SelectOption(
            "LiteLLM",
            "litellm",
            "Use LiteLLM for other providers",
            "3",
        ),
    ]

    result = select_option(model_options, "Select your LLM provider", console)
    if result:
        config.model_type = result.value  # type: ignore

    # Get API key
    console.print()
    api_key = Prompt.ask(
        f"Enter your {config.model_type.upper()} API key",
        password=True,
    )
    config.api_key = api_key

    # Model selection based on provider
    if config.model_type == "openai":
        model_options = [
            SelectOption("gpt-4o", "gpt-4o", "Latest GPT-4o (Recommended)", "1"),
            SelectOption("gpt-4-turbo", "gpt-4-turbo", "GPT-4 Turbo", "2"),
            SelectOption("gpt-4", "gpt-4", "GPT-4", "3"),
            SelectOption("gpt-3.5-turbo", "gpt-3.5-turbo", "GPT-3.5 (Faster, cheaper)", "4"),
        ]
    elif config.model_type == "anthropic":
        model_options = [
            SelectOption("claude-sonnet-4-20250514", "claude-sonnet-4-20250514", "Claude Sonnet 4 (Recommended)", "1"),
            SelectOption("claude-opus-4-20250514", "claude-opus-4-20250514", "Claude Opus 4 (Most capable)", "2"),
            SelectOption("claude-3-5-sonnet-20241022", "claude-3-5-sonnet-20241022", "Claude 3.5 Sonnet", "3"),
        ]
    else:
        model_options = [
            SelectOption("gpt-4o", "gpt-4o", "OpenAI GPT-4o", "1"),
            SelectOption("claude-sonnet-4-20250514", "claude-sonnet-4-20250514", "Anthropic Claude", "2"),
        ]

    console.print()
    result = select_option(model_options, "Select model", console)
    if result:
        config.model = result.value

    # Custom base URL (optional)
    console.print()
    if Confirm.ask("Do you want to set a custom API base URL?", default=False):
        base_url = Prompt.ask("Enter base URL")
        config.base_url = base_url

    # Advanced settings
    console.print()
    if Confirm.ask("Configure advanced settings?", default=False):
        # Max tokens
        max_tokens = Prompt.ask(
            "Max response tokens",
            default=str(config.max_tokens),
        )
        config.max_tokens = int(max_tokens)

        # Temperature
        temp = Prompt.ask(
            "Temperature (0.0-1.0)",
            default=str(config.temperature),
        )
        config.temperature = float(temp)

        # Cache
        config.cache_enabled = Confirm.ask(
            "Enable request caching?",
            default=config.cache_enabled,
        )

    # Save configuration
    console.print()
    if Confirm.ask("Save this configuration?", default=True):
        config.save()
        console.print(f"[green]Configuration saved to {Config.get_config_file()}[/green]")
    else:
        console.print("[yellow]Configuration not saved (will use for this session only)[/yellow]")

    console.print()
    console.print("[bold green]Setup complete![/bold green] You can now use xagent.")
    console.print()

    return config


def check_first_run() -> bool:
    """Check if this is the first run (no config exists)."""
    config_file = Config.get_config_file()
    return not config_file.exists()
