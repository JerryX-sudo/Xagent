"""Utility modules for Xagent."""

from utils.terminal import TerminalUI
from utils.output import OutputManager, CollapsibleOutput
from utils.select import select_option, SelectOption, confirm
from utils.diff import print_diff, print_inline_diff

__all__ = [
    "TerminalUI",
    "OutputManager",
    "CollapsibleOutput",
    "select_option",
    "SelectOption",
    "confirm",
    "print_diff",
    "print_inline_diff",
    "get_logger",
    "setup_logger",
]


def get_logger():
    """Lazy import logger."""
    from utils.logger import get_logger as _get_logger
    return _get_logger()


def setup_logger(level: str = "INFO"):
    """Lazy import and setup logger."""
    from utils.logger import setup_logger as _setup_logger
    return _setup_logger(level)
