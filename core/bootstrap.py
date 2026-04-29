"""Bootstrap and connection test for Xagent."""

import os

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt

from core.config import Config


def get_env_config() -> Config:
    """Get configuration from environment variables."""
    config = Config()
    config.api_key = os.environ.get("XAGENT_API_KEY", "")
    config.base_url = os.environ.get("XAGENT_BASE_URL") or None
    config.model = os.environ.get("XAGENT_MODEL", "gpt-4o")

    # Detect model type from model name or base_url
    model_lower = config.model.lower()
    if "claude" in model_lower:
        config.model_type = "anthropic"
    else:
        config.model_type = "openai"

    return config


def prompt_for_config(console: Console) -> Config:
    """Interactively prompt for configuration."""
    console.print()
    console.print(Panel(
        "[bold cyan]Xagent Setup[/bold cyan]\n\n"
        "Environment variables not found. Please enter your configuration.\n"
        "[dim]You can also set these environment variables:[/dim]\n"
        "  XAGENT_API_KEY, XAGENT_BASE_URL, XAGENT_MODEL",
        border_style="cyan",
    ))
    console.print()

    config = Config()

    # Step 1: API Key
    while True:
        api_key = Prompt.ask(
            "[cyan]API Key[/cyan]",
        )
        if api_key.strip():
            config.api_key = api_key.strip()
            break
        console.print("[red]API key is required[/red]")

    # Step 2: Base URL (optional)
    console.print()
    console.print("[dim]Base URL (press Enter for default OpenAI endpoint)[/dim]")
    base_url = Prompt.ask(
        "[cyan]Base URL[/cyan]",
        default="",
    )
    if base_url.strip():
        config.base_url = base_url.strip()

    # Step 3: Model
    console.print()
    console.print("[dim]Model name (e.g., gpt-4o, claude-sonnet-4-20250514)[/dim]")
    model = Prompt.ask(
        "[cyan]Model[/cyan]",
        default="gpt-4o",
    )
    config.model = model.strip()

    # Detect model type
    if "claude" in config.model.lower():
        config.model_type = "anthropic"
    else:
        config.model_type = "openai"

    return config


def test_connection(config: Config, console: Console) -> tuple[bool, str]:
    """Test LLM connection.

    Returns:
        (success, message)
    """
    from llm import get_llm_client

    console.print()
    console.print("[cyan]Testing connection...[/cyan]")

    try:
        client = get_llm_client(config)
        success, msg = client.validate_connection()
        return success, msg
    except Exception as e:
        return False, str(e)


def _try_fallback_type(config: Config, console: Console) -> tuple[bool, str] | None:
    """Try the other model_type if connection failed.

    Returns (success, msg) if fallback was attempted, None to skip.
    Does NOT fallback if user explicitly set XAGENT_MODEL_TYPE.
    """
    if os.environ.get("XAGENT_MODEL_TYPE"):
        return None

    original_type = config.model_type
    fallback_type = "anthropic" if original_type != "anthropic" else "openai"

    config.model_type = fallback_type
    console.print(f"[dim]Inferred '{original_type}' failed, auto-trying '{fallback_type}'...[/dim]")
    success, msg = test_connection(config, console)

    if success:
        console.print(f"[yellow]Auto-switched to '{fallback_type}' API type[/yellow]")
    else:
        config.model_type = original_type  # revert
    return success, msg


def bootstrap(console: Console) -> Config | None:
    """Bootstrap Xagent configuration.

    Tries environment variables first, then prompts interactively.
    Tests connection before returning.

    Returns:
        Config if successful, None if user cancels
    """
    config = None
    from_env = False
    tried_fallback = False

    while True:
        # First time: try environment variables
        if config is None:
            config = get_env_config()
            if config.api_key:
                console.print("[dim]Using configuration from environment variables[/dim]")
                from_env = True
            else:
                config = prompt_for_config(console)
                from_env = False
            tried_fallback = False

        # Test connection
        success, msg = test_connection(config, console)

        if success:
            console.print("[green]✓ Connection successful![/green]")
            console.print()
            return config
        else:
            console.print(f"[red]✗ Connection failed: {msg}[/red]")
            console.print()

            # Auto-fallback: try the other API type once
            if not tried_fallback:
                tried_fallback = True
                fb_result = _try_fallback_type(config, console)
                if fb_result is not None:
                    success, msg = fb_result
                    if success:
                        console.print("[green]✓ Connection successful![/green]")
                        console.print()
                        return config
                    else:
                        console.print(f"[red]✗ Fallback also failed: {msg}[/red]")
                        console.print()

            # Ask user what to do
            choice = Prompt.ask(
                "[yellow]What would you like to do?[/yellow]",
                choices=["retry", "change", "quit"],
                default="retry"
            )

            if choice == "quit":
                return None
            elif choice == "change":
                config = prompt_for_config(console)
                tried_fallback = False
            # retry: loop again with same config


def print_config_hint(console: Console) -> None:
    """Print hint about environment variables."""
    console.print()
    console.print("[dim]To skip this setup next time, set environment variables:[/dim]")
    console.print("  export XAGENT_API_KEY='your-api-key'")
    console.print("  export XAGENT_MODEL='gpt-4o'  # or claude-sonnet-4-20250514")
    console.print("  export XAGENT_BASE_URL='https://...'  # optional")
    console.print()
