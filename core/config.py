"""Configuration management for Xagent."""

import os
from pathlib import Path
from dataclasses import dataclass, field
from typing import Literal

import yaml


@dataclass
class Config:
    """Configuration for Xagent."""

    api_key: str = ""
    base_url: str | None = None
    model_type: Literal["openai", "anthropic", "litellm"] = "openai"
    model: str = "gpt-4o"
    max_tokens: int = 4096
    temperature: float = 0.7
    cache_ttl: int = 86400  # 24 hours
    cache_enabled: bool = True
    debug: bool = False
    max_iterations: int = 20
    dangerous_commands: list[str] = field(
        default_factory=lambda: ["rm", "sudo", "chmod", "chown", "dd", "mkfs", "kill"]
    )

    @classmethod
    def get_config_dir(cls) -> Path:
        """Get the xagent config directory."""
        config_dir = Path.home() / ".xagent"
        config_dir.mkdir(parents=True, exist_ok=True)
        return config_dir

    @classmethod
    def get_config_file(cls) -> Path:
        """Get the config file path."""
        return cls.get_config_dir() / "config.yaml"

    @classmethod
    def load(cls) -> "Config":
        """Load configuration from environment variables and config file."""
        config = cls()

        # Load from config file first
        config_file = cls.get_config_file()
        if config_file.exists():
            with open(config_file) as f:
                file_config = yaml.safe_load(f) or {}
            for key, value in file_config.items():
                if hasattr(config, key):
                    setattr(config, key, value)

        # Environment variables override file config
        if api_key := os.environ.get("XAGENT_API_KEY"):
            config.api_key = api_key
        if base_url := os.environ.get("XAGENT_BASE_URL"):
            config.base_url = base_url
        if model_type := os.environ.get("XAGENT_MODEL_TYPE"):
            if model_type in ("openai", "anthropic", "litellm"):
                config.model_type = model_type  # type: ignore
        if model := os.environ.get("XAGENT_MODEL"):
            config.model = model

        return config

    def save(self) -> None:
        """Save current configuration to file."""
        config_file = self.get_config_file()
        data = {
            "api_key": self.api_key,
            "base_url": self.base_url,
            "model_type": self.model_type,
            "model": self.model,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "cache_ttl": self.cache_ttl,
            "cache_enabled": self.cache_enabled,
            "dangerous_commands": self.dangerous_commands,
        }
        with open(config_file, "w") as f:
            yaml.dump(data, f, default_flow_style=False)

    def validate(self) -> tuple[bool, str]:
        """Validate the configuration."""
        if not self.api_key:
            return False, "API key not set. Set XAGENT_API_KEY or configure in ~/.xagent/config.yaml"
        return True, "Configuration valid"
