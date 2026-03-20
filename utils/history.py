"""Command line history for Xagent."""

import sys
import tty
import termios
from pathlib import Path
from dataclasses import dataclass, field

from rich.console import Console

from core.config import Config


@dataclass
class InputHistory:
    """Manages command line input history."""

    max_size: int = 1000
    _history: list[str] = field(default_factory=list)
    _position: int = 0
    _current_input: str = ""

    def __post_init__(self):
        self._load()

    def _get_history_file(self) -> Path:
        """Get history file path."""
        return Config.get_config_dir() / "history"

    def _load(self) -> None:
        """Load history from file."""
        history_file = self._get_history_file()
        if history_file.exists():
            try:
                lines = history_file.read_text().strip().split('\n')
                self._history = [l for l in lines if l][-self.max_size:]
            except Exception:
                self._history = []
        self._position = len(self._history)

    def _save(self) -> None:
        """Save history to file."""
        history_file = self._get_history_file()
        try:
            history_file.write_text('\n'.join(self._history[-self.max_size:]))
        except Exception:
            pass

    def add(self, command: str) -> None:
        """Add a command to history."""
        command = command.strip()
        if not command:
            return
        # Don't add duplicates of the last command
        if self._history and self._history[-1] == command:
            return
        self._history.append(command)
        self._position = len(self._history)
        self._save()

    def previous(self) -> str | None:
        """Get previous command in history."""
        if self._position > 0:
            self._position -= 1
            return self._history[self._position]
        return None

    def next(self) -> str | None:
        """Get next command in history."""
        if self._position < len(self._history) - 1:
            self._position += 1
            return self._history[self._position]
        elif self._position == len(self._history) - 1:
            self._position = len(self._history)
            return self._current_input
        return None

    def reset_position(self) -> None:
        """Reset position to end of history."""
        self._position = len(self._history)

    def set_current(self, text: str) -> None:
        """Set current input text (for restoration)."""
        self._current_input = text

    def search(self, prefix: str) -> list[str]:
        """Search history for commands starting with prefix."""
        return [h for h in reversed(self._history) if h.startswith(prefix)][:10]

    def clear(self) -> None:
        """Clear all history."""
        self._history.clear()
        self._position = 0
        self._get_history_file().unlink(missing_ok=True)


def read_input_with_history(
    prompt: str,
    history: InputHistory,
    console: Console | None = None,
) -> str:
    """Read input with arrow key history navigation.

    Args:
        prompt: Prompt to display
        history: InputHistory instance
        console: Rich console

    Returns:
        User input string
    """
    if console is None:
        console = Console()

    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)

    current_input = ""
    cursor_pos = 0
    history.reset_position()

    def refresh_line():
        """Redraw the current line."""
        # Clear line and rewrite
        sys.stdout.write('\r\033[K')  # Clear line
        sys.stdout.write(prompt)
        sys.stdout.write(current_input)
        # Move cursor to position
        if cursor_pos < len(current_input):
            sys.stdout.write(f'\033[{len(current_input) - cursor_pos}D')
        sys.stdout.flush()

    try:
        tty.setraw(fd)
        console.print(prompt, end="")
        sys.stdout.flush()

        while True:
            ch = sys.stdin.read(1)

            if ch == '\r' or ch == '\n':  # Enter
                sys.stdout.write('\n')
                sys.stdout.flush()
                break

            elif ch == '\x03':  # Ctrl+C
                sys.stdout.write('\n')
                raise KeyboardInterrupt

            elif ch == '\x04':  # Ctrl+D
                if not current_input:
                    raise EOFError
                continue

            elif ch == '\x7f' or ch == '\x08':  # Backspace
                if cursor_pos > 0:
                    current_input = current_input[:cursor_pos-1] + current_input[cursor_pos:]
                    cursor_pos -= 1
                    refresh_line()

            elif ch == '\x1b':  # Escape sequence
                ch2 = sys.stdin.read(1)
                if ch2 == '[':
                    ch3 = sys.stdin.read(1)
                    if ch3 == 'A':  # Up arrow
                        history.set_current(current_input)
                        prev = history.previous()
                        if prev is not None:
                            current_input = prev
                            cursor_pos = len(current_input)
                            refresh_line()
                    elif ch3 == 'B':  # Down arrow
                        next_cmd = history.next()
                        if next_cmd is not None:
                            current_input = next_cmd
                            cursor_pos = len(current_input)
                            refresh_line()
                    elif ch3 == 'C':  # Right arrow
                        if cursor_pos < len(current_input):
                            cursor_pos += 1
                            sys.stdout.write('\033[C')
                            sys.stdout.flush()
                    elif ch3 == 'D':  # Left arrow
                        if cursor_pos > 0:
                            cursor_pos -= 1
                            sys.stdout.write('\033[D')
                            sys.stdout.flush()
                    elif ch3 == '3':  # Delete key (followed by ~)
                        sys.stdin.read(1)  # consume ~
                        if cursor_pos < len(current_input):
                            current_input = current_input[:cursor_pos] + current_input[cursor_pos+1:]
                            refresh_line()
                    elif ch3 == 'H':  # Home
                        cursor_pos = 0
                        refresh_line()
                    elif ch3 == 'F':  # End
                        cursor_pos = len(current_input)
                        refresh_line()

            elif ch == '\x01':  # Ctrl+A (home)
                cursor_pos = 0
                refresh_line()

            elif ch == '\x05':  # Ctrl+E (end)
                cursor_pos = len(current_input)
                refresh_line()

            elif ch == '\x0b':  # Ctrl+K (kill to end)
                current_input = current_input[:cursor_pos]
                refresh_line()

            elif ch == '\x15':  # Ctrl+U (kill to start)
                current_input = current_input[cursor_pos:]
                cursor_pos = 0
                refresh_line()

            elif ch == '\x17':  # Ctrl+W (delete word)
                # Find word boundary
                pos = cursor_pos
                while pos > 0 and current_input[pos-1] == ' ':
                    pos -= 1
                while pos > 0 and current_input[pos-1] != ' ':
                    pos -= 1
                current_input = current_input[:pos] + current_input[cursor_pos:]
                cursor_pos = pos
                refresh_line()

            elif ch >= ' ' and ch <= '~':  # Printable characters
                current_input = current_input[:cursor_pos] + ch + current_input[cursor_pos:]
                cursor_pos += 1
                refresh_line()

    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)

    return current_input
