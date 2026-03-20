"""Logging utilities for Xagent."""

import logging
from pathlib import Path

from core.config import Config


_logger: logging.Logger | None = None


def setup_logger(level: str = "INFO") -> logging.Logger:
    """Setup and return the logger."""
    global _logger

    if _logger:
        return _logger

    log_dir = Config.get_config_dir() / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "xagent.log"

    _logger = logging.getLogger("xagent")
    _logger.setLevel(getattr(logging, level.upper()))

    # File handler
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(logging.DEBUG)
    file_formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    file_handler.setFormatter(file_formatter)
    _logger.addHandler(file_handler)

    # Console handler (only for warnings and above)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.WARNING)
    console_formatter = logging.Formatter("%(levelname)s: %(message)s")
    console_handler.setFormatter(console_formatter)
    _logger.addHandler(console_handler)

    return _logger


def get_logger() -> logging.Logger:
    """Get the logger, setting it up if needed."""
    global _logger
    if not _logger:
        return setup_logger()
    return _logger
