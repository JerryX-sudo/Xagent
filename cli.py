"""CLI entry point for Xagent."""

import os
import sys
import subprocess
from datetime import datetime

import click
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from core import Config, Session, SkillRegistry
from core.agent import Agent
from core.bootstrap import bootstrap, get_env_config, test_connection, print_config_hint
from core.export import export_to_markdown
from core.theme import Theme, get_theme, set_theme
from utils.terminal import TerminalUI
from utils.history import InputHistory, read_input_with_history, KeyboardMonitor
from utils.menu import MenuItem, show_menu, show_config_editor


console = Console()
ui = TerminalUI()


# Define all available commands
COMMANDS = [
    MenuItem("help", "Show help message"),
    MenuItem("clear", "Clear conversation history"),
    MenuItem("resume", "Resume a recent session"),
    MenuItem("config", "Edit configuration (model, max_iterations, etc.)"),
    MenuItem("memory", "Manage static memory"),
    MenuItem("history", "Show conversation history"),
    MenuItem("save", "Save current session"),
    MenuItem("load", "Load a saved session"),
    MenuItem("sessions", "List saved sessions"),
    MenuItem("cache", "Manage request cache"),
    MenuItem("tools", "List available tools"),
    MenuItem("skills", "List available skills"),
    MenuItem("permissions", "Manage tool permissions"),
    MenuItem("export", "Export conversation to markdown"),
    MenuItem("theme", "Change color theme"),
    MenuItem("exit", "Exit Xagent"),
]


def show_command_menu() -> str | None:
    """Show interactive command menu. Returns selected command or None."""
    result = show_menu(COMMANDS, "Commands", console)
    if result:
        return f"/{result.name}"
    return None


def handle_config(agent: Agent) -> None:
    """Handle interactive config editing."""
    config = agent.config

    def set_model(v):
        config.model = v

    def set_max_iterations(v):
        try:
            config.max_iterations = int(v)
            agent.max_iterations = int(v)
        except ValueError:
            ui.print_error("Invalid number")

    def set_temperature(v):
        try:
            config.temperature = float(v)
        except ValueError:
            ui.print_error("Invalid number")

    def set_max_tokens(v):
        try:
            config.max_tokens = int(v)
        except ValueError:
            ui.print_error("Invalid number")

    def set_base_url(v):
        config.base_url = v if v else None

    def set_api_key(v):
        config.api_key = v

    def set_model_type(v):
        if v in ("openai", "anthropic", "litellm"):
            config.model_type = v
        else:
            ui.print_error("Invalid model type. Use: openai, anthropic, or litellm")

    def toggle_reasoning(v):
        config.reasoning_enabled = v.lower() in ("true", "yes", "1", "on")

    config_items = [
        ("Model Type", "API type (openai, anthropic, or litellm)", config.model_type, set_model_type),
        ("Model", "LLM model to use", config.model, set_model),
        ("Max Iterations", "Maximum agent loop iterations", str(config.max_iterations), set_max_iterations),
        ("Temperature", "Model temperature (0-1)", str(config.temperature), set_temperature),
        ("Max Tokens", "Maximum response tokens", str(config.max_tokens), set_max_tokens),
        ("Base URL", "API base URL (optional)", config.base_url or "", set_base_url),
        ("Reasoning", "Enable thinking/reasoning (true/false)", str(config.reasoning_enabled).lower(), toggle_reasoning),
        ("API Key", "API key", config.api_key, set_api_key),
    ]

    show_config_editor(config_items, "Configuration", console)

    # Save config to disk
    config.save()
    ui.print_success("Configuration saved to ~/.xagent/config.yaml")


def handle_memory_menu(agent: Agent) -> None:
    """Handle memory submenu."""
    items = [
        MenuItem("view", "View static memory"),
        MenuItem("add", "Add to static memory"),
        MenuItem("clear", "Clear static memory"),
    ]

    result = show_menu(items, "Memory", console)
    if result:
        if result.name == "view":
            content = agent.static_memory.read()
            console.print(content)
        elif result.name == "add":
            console.print("[cyan]Enter text to add to memory:[/cyan]")
            try:
                text = input("> ").strip()
                if text:
                    agent.static_memory.append(text)
                    agent.refresh_memory()
                    ui.print_success("Added to memory")
            except (KeyboardInterrupt, EOFError):
                pass
        elif result.name == "clear":
            agent.static_memory.clear()
            agent.refresh_memory()
            ui.print_success("Memory cleared")


def handle_resume(agent: Agent) -> bool:
    """Handle /resume command. Returns True if session was resumed."""
    sessions = Session.list_resumable_sessions()

    if not sessions:
        ui.console.print("[dim]No recent sessions to resume[/dim]")
        return False

    # Build menu items
    items = []
    for i, s in enumerate(sessions):
        # Format time
        try:
            updated = datetime.fromisoformat(s["updated_at"])
            time_str = updated.strftime("%m/%d %H:%M")
        except (ValueError, KeyError):
            time_str = "unknown"

        title = s["title"] or "(no title)"
        if len(title) > 40:
            title = title[:37] + "..."

        items.append(MenuItem(
            s["session_id"],
            f"{title} ({s['message_count']} msgs, {time_str})",
        ))

    ui.console.print("[cyan]Recent sessions (expires after 7 days):[/cyan]")
    result = show_menu(items, "Resume Session", console)

    if result:
        try:
            loaded = Session.load(result.name, auto=True)
            # Transfer to agent
            agent.session = loaded
            ui.print_success(f"Resumed session: {loaded.title or loaded.session_id}")
            ui.console.print()

            # Replay full conversation history
            _print_conversation_history(loaded.messages)

            return True
        except FileNotFoundError:
            ui.print_error("Session not found")
            return False

    return False


def _print_conversation_history(messages: list) -> None:
    """Print conversation history in a nice format."""
    console.print()
    console.print(Panel.fit(
        "[bold]Conversation History[/bold]",
        border_style="dim cyan",
    ))
    console.print()

    for msg in messages:
        if msg.role == "system":
            continue
        elif msg.role == "user":
            # User message with bubble style
            text = Text()
            text.append("  ▶ ", style="bold green")
            text.append(msg.content, style="white")
            console.print(text)
            console.print()
        elif msg.role == "assistant":
            if msg.content:
                # Agent message with different style
                text = Text()
                text.append("  ◀ ", style="bold cyan")
                text.append(msg.content, style="dim white")
                console.print(text)
                console.print()
        elif msg.role == "tool":
            # Tool result - compact inline
            tool_name = msg.name or "tool"
            preview = msg.content[:80] + "..." if len(msg.content) > 80 else msg.content
            preview = preview.replace("\n", " ")
            console.print(f"    [dim]⚙ {tool_name} → {preview}[/dim]")

    console.print(Panel.fit(
        "[dim]Continue the conversation below[/dim]",
        border_style="dim cyan",
    ))
    console.print()


def handle_command(cmd: str, agent: Agent, skills: SkillRegistry) -> bool:
    """Handle slash commands. Returns True if should continue, False to exit."""
    parts = cmd.strip().split(maxsplit=2)
    command = parts[0].lower()

    # Check if it's a skill
    if command.startswith("/"):
        skill_name = command[1:]
        skill = skills.get(skill_name)
        if skill and skill_name not in ("exit", "quit", "help", "clear", "history",
                                         "memory", "save", "load", "sessions",
                                         "cache", "config", "tools", "skills",
                                         "export", "theme", "permissions"):
            result = skill.run()
            if result.startswith("SKILL:"):
                agent.run(f"Execute skill: {result}", stream=True)
            else:
                ui.console.print(result)
            return True

    if command in ("/exit", "/quit"):
        ui.print_info("Goodbye!")
        return False

    elif command == "/help":
        ui.print_help()

    elif command == "/clear":
        agent.session.clear()
        agent._init_system_prompt()
        ui.print_success("Conversation cleared")

    elif command == "/resume":
        handle_resume(agent)

    elif command == "/history":
        for msg in agent.session.messages:
            if msg.role != "system":
                content_preview = msg.content[:100] if msg.content else "(no content)"
                ui.console.print(f"[dim]{msg.role}:[/dim] {content_preview}")

    elif command == "/memory":
        if len(parts) == 1:
            # Show interactive menu
            handle_memory_menu(agent)
        elif parts[1] == "add" and len(parts) > 2:
            agent.static_memory.append(parts[2])
            agent.refresh_memory()
            ui.print_success("Added to memory")
        elif parts[1] == "clear":
            agent.static_memory.clear()
            agent.refresh_memory()
            ui.print_success("Memory cleared")
        elif parts[1] == "view":
            content = agent.static_memory.read()
            ui.console.print(content)
        else:
            ui.print_error("Usage: /memory [view | add <text> | clear]")

    elif command == "/save":
        name = parts[1] if len(parts) > 1 else None
        path = agent.session.save(name)
        ui.print_success(f"Session saved to {path}")

    elif command == "/load":
        if len(parts) < 2:
            ui.print_error("Usage: /load <session_name>")
        else:
            try:
                agent.session = Session.load(parts[1])
                ui.print_success(f"Session '{parts[1]}' loaded")
            except FileNotFoundError:
                ui.print_error(f"Session '{parts[1]}' not found")

    elif command == "/sessions":
        sessions = Session.list_sessions()
        if sessions:
            ui.console.print("[cyan]Saved sessions:[/cyan]")
            for s in sessions:
                ui.console.print(f"  - {s}")
        else:
            ui.console.print("[dim]No saved sessions[/dim]")

    elif command == "/cache":
        if len(parts) > 1 and parts[1] == "clear":
            count = agent.cache.clear()
            ui.print_success(f"Cleared {count} cached items")
        else:
            stats = agent.cache.stats()
            ui.console.print("[cyan]Cache Statistics:[/cyan]")
            for key, value in stats.items():
                ui.console.print(f"  {key}: {value}")

    elif command == "/config":
        if len(parts) == 1:
            # Show interactive config editor
            handle_config(agent)
        else:
            # Show current config
            ui.console.print("[cyan]Current Configuration:[/cyan]")
            ui.console.print(f"  Model Type: {agent.config.model_type}")
            ui.console.print(f"  Model: {agent.config.model}")
            ui.console.print(f"  Base URL: {agent.config.base_url or 'default'}")
            ui.console.print(f"  Max Tokens: {agent.config.max_tokens}")
            ui.console.print(f"  Max Iterations: {agent.config.max_iterations}")
            ui.console.print(f"  Temperature: {agent.config.temperature}")
            ui.console.print(f"  Cache Enabled: {agent.config.cache_enabled}")

    elif command == "/tools":
        tools = agent.tools.list_tools()
        ui.console.print("[cyan]Available Tools:[/cyan]")
        for tool_name in tools:
            tool = agent.tools.get(tool_name)
            if tool:
                ui.console.print(f"  [bold]{tool_name}[/bold]: {tool.description[:60]}...")

    elif command == "/skills":
        skill_names = skills.list_skills()
        ui.console.print("[cyan]Available Skills:[/cyan]")
        for name in skill_names:
            skill = skills.get(name)
            if skill:
                ui.console.print(f"  [bold]/{name}[/bold]: {skill.description}")

    elif command == "/export":
        name = parts[1] if len(parts) > 1 else None
        try:
            path = export_to_markdown(agent.session, name)
            ui.print_success(f"Exported to {path}")
        except Exception as e:
            ui.print_error(f"Export failed: {e}")

    elif command == "/theme":
        if len(parts) > 1:
            theme_name = parts[1]
            if theme_name == "list":
                themes = Theme.list_themes()
                ui.console.print("[cyan]Available themes:[/cyan]")
                for t in themes:
                    ui.console.print(f"  - {t}")
            else:
                try:
                    set_theme(theme_name)
                    ui.print_success(f"Theme set to '{theme_name}'")
                except Exception as e:
                    ui.print_error(f"Failed to set theme: {e}")
        else:
            ui.console.print(f"[cyan]Current theme:[/cyan] {get_theme()}")
            ui.console.print("[dim]Use /theme list to see available themes[/dim]")
            ui.console.print("[dim]Use /theme <name> to switch theme[/dim]")

    elif command == "/permissions":
        if len(parts) > 1:
            subcmd = parts[1]
            if subcmd == "list":
                perms = agent.permission_manager.list_task_permissions()
                if perms:
                    ui.console.print("[cyan]Task-level permissions:[/cyan]")
                    for p in perms:
                        ui.console.print(f"  - {p}")
                else:
                    ui.console.print("[dim]No task-level permissions active[/dim]")
            elif subcmd == "revoke":
                if len(parts) > 2:
                    tool_name = parts[2]
                    if agent.permission_manager.revoke_task_permission(tool_name):
                        ui.print_success(f"Revoked permission for {tool_name}")
                    else:
                        ui.print_error(f"No permission found for {tool_name}")
                else:
                    count = agent.permission_manager.revoke_all_task_permissions()
                    ui.print_success(f"Revoked {count} permissions")
            elif subcmd == "pause":
                agent.permission_manager.pause_task_mode()
                ui.print_success("Task-mode auto-approve paused")
            elif subcmd == "resume":
                agent.permission_manager.resume_task_mode()
                ui.print_success("Task-mode auto-approve resumed")
            else:
                ui.print_error(f"Unknown subcommand: {subcmd}")
        else:
            ui.console.print("[cyan]Permission Commands:[/cyan]")
            ui.console.print("  /permissions list       - List active task-level permissions")
            ui.console.print("  /permissions revoke     - Revoke all task-level permissions")
            ui.console.print("  /permissions revoke <tool> - Revoke permission for a tool")
            ui.console.print("  /permissions pause      - Pause auto-approve (ask every time)")
            ui.console.print("  /permissions resume     - Resume auto-approve")

    else:
        ui.print_error(f"Unknown command: {command}")

    return True


@click.group(invoke_without_command=True)
@click.pass_context
def main(ctx):
    """Xagent - A lightweight terminal Agent framework."""
    if ctx.invoked_subcommand is None:
        run_interactive()


@click.command()
def update():
    """Update Xagent to the latest version."""
    ui.print_info("Updating Xagent...")

    repo_url = os.environ.get("XAGENT_REPO_URL")
    if not repo_url:
        try:
            result = subprocess.run(
                ["git", "remote", "get-url", "origin"],
                capture_output=True,
                encoding="utf-8",
                errors="replace",
                cwd=os.path.dirname(os.path.abspath(__file__)),
            )
            if result.returncode == 0:
                repo_url = result.stdout.strip()
        except Exception:
            pass

    if not repo_url:
        ui.print_error("Could not determine repository URL. Set XAGENT_REPO_URL environment variable.")
        return

    try:
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", "--upgrade", f"git+{repo_url}"],
            capture_output=True,
            encoding="utf-8",
            errors="replace",
        )
        if result.returncode == 0:
            ui.print_success("Xagent updated successfully!")
        else:
            ui.print_error(f"Update failed: {result.stderr}")
    except Exception as e:
        ui.print_error(f"Update failed: {e}")


@click.command()
@click.argument("message", nargs=-1)
def ask(message):
    """Ask a single question without entering interactive mode."""
    if not message:
        ui.print_error("Please provide a message")
        return

    # Bootstrap configuration
    config = bootstrap(console)
    if config is None:
        return

    agent = Agent(config, ui=ui)
    agent.tools.load_plugins()

    user_message = " ".join(message)
    agent.run(user_message, stream=True)


# Register commands
main.add_command(update)
main.add_command(ask)


def run_interactive():
    """Run the interactive CLI loop."""
    # Bootstrap configuration (env vars or interactive prompt)
    config = bootstrap(console)
    if config is None:
        print_config_hint(console)
        return

    # Initialize components
    session = Session()
    agent = Agent(config, session, ui)
    skills = SkillRegistry()
    history = InputHistory()

    # Load plugins and skills
    plugin_count = agent.tools.load_plugins()
    skill_count = skills.load_skills_from_dir()

    if plugin_count > 0:
        ui.print_info(f"Loaded {plugin_count} plugins")
    if skill_count > 0:
        ui.print_info(f"Loaded {skill_count} skills")

    # Print welcome
    ui.print_welcome()

    # Create keyboard monitor for interrupting during agent execution
    def on_escape():
        if agent.is_running():
            agent.interrupt()

    kb_monitor = KeyboardMonitor(on_escape)

    # Main loop
    while True:
        try:
            user_input = read_input_with_history("  ▶ ", history, ui.console)

            if not user_input.strip():
                continue

            # Add to history
            history.add(user_input)

            # Handle commands
            if user_input == "/":
                # Show interactive command menu
                selected = show_command_menu()
                if selected:
                    if not handle_command(selected, agent, skills):
                        break
                continue
            elif user_input.startswith("/"):
                if not handle_command(user_input, agent, skills):
                    break
                continue

            # Run agent with keyboard monitoring
            kb_monitor.start()
            try:
                agent.run(user_input, stream=True)
            finally:
                kb_monitor.stop()

            # Auto-save session after each interaction
            if len(agent.session.messages) > 1:  # Has more than just system prompt
                try:
                    agent.session.save(auto=True)
                except Exception:
                    pass  # Silent fail for auto-save

            # Show continuation hint if interrupted
            if agent.was_interrupted():
                ui.print_warning("Interrupted - type to continue or /clear to restart")
                agent.clear_interrupt()

        except KeyboardInterrupt:
            # ESC pressed during input - just show hint
            ui.console.print()
            ui.print_warning("Interrupted - type to continue or /clear to restart")
        except EOFError:
            # Ctrl+C or Ctrl+D - exit program
            ui.console.print()
            ui.print_info("Goodbye!")
            break
        except Exception as e:
            ui.print_error(str(e))

    # Final auto-save before exit
    if len(agent.session.messages) > 1:
        try:
            agent.session.save(auto=True)
        except Exception:
            pass

    # Cleanup
    agent.cache.close()


if __name__ == "__main__":
    main()
