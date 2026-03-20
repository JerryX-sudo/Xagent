"""Theme configuration for Xagent."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from core.config import Config


@dataclass
class Theme:
    """Color theme configuration."""

    # Main colors
    primary: str = "cyan"
    secondary: str = "blue"
    success: str = "green"
    warning: str = "yellow"
    error: str = "red"
    muted: str = "dim"

    # UI elements
    prompt_user: str = "bold green"
    prompt_agent: str = "bold blue"
    prompt_system: str = "dim"

    # Diff colors
    diff_add: str = "green"
    diff_remove: str = "red"
    diff_context: str = "dim"

    # Panel borders
    border_default: str = "blue"
    border_warning: str = "yellow"
    border_error: str = "red"
    border_success: str = "green"

    # Tool output
    tool_name: str = "magenta"
    tool_args: str = "dim"

    # Code
    code_keyword: str = "blue"
    code_string: str = "green"
    code_comment: str = "dim"

    @classmethod
    def load(cls, name: str = "default") -> "Theme":
        """Load a theme by name."""
        themes_dir = Config.get_config_dir() / "themes"

        # Check for custom theme
        theme_file = themes_dir / f"{name}.yaml"
        if theme_file.exists():
            try:
                with open(theme_file) as f:
                    data = yaml.safe_load(f) or {}
                return cls(**{k: v for k, v in data.items() if hasattr(cls, k)})
            except Exception:
                pass

        # Return built-in themes
        if name == "dark":
            return cls()  # Default is dark
        elif name == "light":
            return cls(
                primary="blue",
                secondary="cyan",
                prompt_user="bold blue",
                prompt_agent="bold magenta",
            )
        elif name == "minimal":
            return cls(
                primary="white",
                secondary="white",
                prompt_user="bold",
                prompt_agent="bold",
                border_default="white",
            )
        elif name == "colorful":
            return cls(
                primary="cyan",
                secondary="magenta",
                prompt_user="bold yellow",
                prompt_agent="bold cyan",
                tool_name="bold magenta",
            )

        return cls()

    def save(self, name: str) -> Path:
        """Save theme to file."""
        themes_dir = Config.get_config_dir() / "themes"
        themes_dir.mkdir(parents=True, exist_ok=True)

        theme_file = themes_dir / f"{name}.yaml"
        data = {
            "primary": self.primary,
            "secondary": self.secondary,
            "success": self.success,
            "warning": self.warning,
            "error": self.error,
            "muted": self.muted,
            "prompt_user": self.prompt_user,
            "prompt_agent": self.prompt_agent,
            "prompt_system": self.prompt_system,
            "diff_add": self.diff_add,
            "diff_remove": self.diff_remove,
            "diff_context": self.diff_context,
            "border_default": self.border_default,
            "border_warning": self.border_warning,
            "border_error": self.border_error,
            "border_success": self.border_success,
            "tool_name": self.tool_name,
            "tool_args": self.tool_args,
        }

        with open(theme_file, "w") as f:
            yaml.dump(data, f, default_flow_style=False)

        return theme_file

    @classmethod
    def list_themes(cls) -> list[str]:
        """List available themes."""
        builtin = ["default", "dark", "light", "minimal", "colorful"]

        themes_dir = Config.get_config_dir() / "themes"
        custom = []
        if themes_dir.exists():
            custom = [f.stem for f in themes_dir.glob("*.yaml")]

        return builtin + [t for t in custom if t not in builtin]


# Global theme instance
_current_theme: Theme | None = None


def get_theme() -> Theme:
    """Get the current theme."""
    global _current_theme
    if _current_theme is None:
        # Try to load from config
        config = Config.load()
        theme_name = getattr(config, 'theme', 'default')
        _current_theme = Theme.load(theme_name)
    return _current_theme


def set_theme(theme: Theme | str) -> None:
    """Set the current theme."""
    global _current_theme
    if isinstance(theme, str):
        _current_theme = Theme.load(theme)
    else:
        _current_theme = theme
