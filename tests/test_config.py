"""Tests for configuration module."""

import sys
from pathlib import Path

# Ensure correct path
sys.path.insert(0, str(Path(__file__).parent.parent))

import os
import tempfile

import pytest

from core.config import Config


class TestConfig:
    """Tests for Config class."""

    def test_default_values(self):
        """Test default configuration values."""
        config = Config()
        assert config.api_key == ""
        assert config.model_type == "openai"
        assert config.model == "gpt-4o"
        assert config.max_tokens == 4096
        assert config.temperature == 0.7
        assert config.cache_enabled is True

    def test_validate_missing_api_key(self):
        """Test validation fails without API key."""
        config = Config()
        valid, msg = config.validate()
        assert valid is False
        assert "API key" in msg

    def test_validate_with_api_key(self):
        """Test validation passes with API key."""
        config = Config(api_key="test-key")
        valid, msg = config.validate()
        assert valid is True

    def test_env_override(self):
        """Test environment variables override config."""
        os.environ["XAGENT_API_KEY"] = "env-test-key"
        os.environ["XAGENT_MODEL"] = "gpt-3.5-turbo"

        try:
            config = Config.load()
            assert config.api_key == "env-test-key"
            assert config.model == "gpt-3.5-turbo"
        finally:
            del os.environ["XAGENT_API_KEY"]
            del os.environ["XAGENT_MODEL"]

    def test_save_and_load(self, tmp_path, monkeypatch):
        """Test saving and loading config."""
        # Use temp directory
        monkeypatch.setattr(Config, "get_config_dir", lambda: tmp_path)

        config = Config(api_key="save-test", model="test-model")
        config.save()

        loaded = Config.load()
        assert loaded.api_key == "save-test"
        assert loaded.model == "test-model"
