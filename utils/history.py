"""Command line history for Xagent."""

import os
import sys
import threading
from pathlib import Path
from dataclasses import dataclass, field

from rich.console import Console

from core.config import Config
from utils.compat import (
    IS_WINDOWS,
    get_terminal_settings,
    set_terminal_settings,
    set_cbreak_mode,
    set_raw_mode,
    select_stdin,
    set_nonblocking,
    restore_blocking,
)

if IS_WINDOWS:
    import msvcrt
else:
    import tty
    import termios
    import fcntl


class KeyboardMonitor:
    """Monitor keyboard for ESC during agent execution."""

    # Global instance for access from tools
    _instance = None

    def __init__(self, on_escape: callable):
        self._on_escape = on_escape
        self._stop = threading.Event()
        self._thread = None
        self._original_settings = None
        KeyboardMonitor._instance = self

    def start(self) -> None:
        """Start monitoring keyboard in background."""
        if self._thread and self._thread.is_alive():
            return

        self._stop.clear()
        self._thread = threading.Thread(target=self._monitor, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        """Stop monitoring and restore terminal."""
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=0.3)
            self._thread = None

    def _monitor(self) -> None:
        """Monitor stdin for ESC key."""
        if IS_WINDOWS:
            self._monitor_windows()
        else:
            self._monitor_unix()

    def _monitor_windows(self) -> None:
        """Windows-specific keyboard monitoring."""
        while not self._stop.is_set():
            if msvcrt.kbhit():
                ch = msvcrt.getwch()
                if ch == '\x1b':  # ESC
                    self._on_escape()
                    break
                elif ch == '\x03':  # Ctrl+C
                    self._on_escape()
                    break
            self._stop.wait(0.1)

    def _monitor_unix(self) -> None:
        """Unix-specific keyboard monitoring."""
        fd = sys.stdin.fileno()
        old_flags = None

        try:
            self._original_settings = termios.tcgetattr(fd)
            old_flags = fcntl.fcntl(fd, fcntl.F_GETFL)

            # Set cbreak mode
            new_settings = termios.tcgetattr(fd)
            new_settings[3] = new_settings[3] & ~termios.ICANON & ~termios.ECHO
            termios.tcsetattr(fd, termios.TCSANOW, new_settings)

            while not self._stop.is_set():
                if select_stdin(0.1):
                    try:
                        fcntl.fcntl(fd, fcntl.F_SETFL, old_flags | os.O_NONBLOCK)
                        try:
                            ch = sys.stdin.read(1)
                            if ch == '\x1b':  # ESC
                                try:
                                    ch2 = sys.stdin.read(1)
                                except (IOError, BlockingIOError):
                                    ch2 = None
                                if ch2 is None or ch2 == '':
                                    self._on_escape()
                                    break
                            elif ch == '\x03':  # Ctrl+C
                                self._on_escape()
                                break
                        except (IOError, BlockingIOError):
                            pass
                        finally:
                            fcntl.fcntl(fd, fcntl.F_SETFL, old_flags)
                    except Exception:
                        pass
        except Exception:
            pass
        finally:
            if old_flags is not None:
                try:
                    fcntl.fcntl(fd, fcntl.F_SETFL, old_flags)
                except Exception:
                    pass
            if self._original_settings:
                try:
                    termios.tcsetattr(fd, termios.TCSADRAIN, self._original_settings)
                except Exception:
                    pass


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
    """Read input with arrow key history navigation."""
    if console is None:
        console = Console()

    if IS_WINDOWS:
        return _read_input_windows(prompt, history, console)
    else:
        return _read_input_unix(prompt, history, console)


def _read_input_windows(prompt: str, history: InputHistory, console: Console) -> str:
    """Windows-specific input reading with history."""
    current_input = ""
    cursor_pos = 0
    history.reset_position()

    sys.stdout.write(prompt)
    sys.stdout.flush()

    while True:
        ch = msvcrt.getwch()

        if ch == '\r':  # Enter
            sys.stdout.write('\n')
            sys.stdout.flush()
            break

        elif ch == '\x03':  # Ctrl+C
            sys.stdout.write('\n')
            raise EOFError

        elif ch == '\x08':  # Backspace
            if cursor_pos > 0:
                current_input = current_input[:cursor_pos-1] + current_input[cursor_pos:]
                cursor_pos -= 1
                _refresh_line_windows(prompt, current_input, cursor_pos)

        elif ch == '\x00' or ch == '\xe0':  # Special key prefix
            ch2 = msvcrt.getwch()
            if ch2 == 'H':  # Up arrow
                history.set_current(current_input)
                prev = history.previous()
                if prev is not None:
                    current_input = prev
                    cursor_pos = len(current_input)
                    _refresh_line_windows(prompt, current_input, cursor_pos)
            elif ch2 == 'P':  # Down arrow
                next_cmd = history.next()
                if next_cmd is not None:
                    current_input = next_cmd
                    cursor_pos = len(current_input)
                    _refresh_line_windows(prompt, current_input, cursor_pos)
            elif ch2 == 'M':  # Right arrow
                if cursor_pos < len(current_input):
                    cursor_pos += 1
                    _refresh_line_windows(prompt, current_input, cursor_pos)
            elif ch2 == 'K':  # Left arrow
                if cursor_pos > 0:
                    cursor_pos -= 1
                    _refresh_line_windows(prompt, current_input, cursor_pos)
            elif ch2 == 'S':  # Delete
                if cursor_pos < len(current_input):
                    current_input = current_input[:cursor_pos] + current_input[cursor_pos+1:]
                    _refresh_line_windows(prompt, current_input, cursor_pos)
            elif ch2 == 'G':  # Home
                cursor_pos = 0
                _refresh_line_windows(prompt, current_input, cursor_pos)
            elif ch2 == 'O':  # End
                cursor_pos = len(current_input)
                _refresh_line_windows(prompt, current_input, cursor_pos)

        elif ch == '\x1b':  # ESC
            sys.stdout.write('\n')
            raise KeyboardInterrupt

        elif ch >= ' ':  # Printable
            current_input = current_input[:cursor_pos] + ch + current_input[cursor_pos:]
            cursor_pos += 1
            _refresh_line_windows(prompt, current_input, cursor_pos)

    return current_input


def _refresh_line_windows(prompt: str, text: str, cursor_pos: int) -> None:
    """Refresh the input line on Windows."""
    sys.stdout.write('\r' + ' ' * (len(prompt) + len(text) + 5) + '\r')
    sys.stdout.write(prompt + text)
    if cursor_pos < len(text):
        sys.stdout.write('\b' * (len(text) - cursor_pos))
    sys.stdout.flush()


def _read_input_unix(prompt: str, history: InputHistory, console: Console) -> str:
    """Unix-specific input reading with history."""
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)

    current_input = ""
    cursor_pos = 0
    history.reset_position()

    last_num_lines = [1]

    def get_display_width(s: str) -> int:
        width = 0
        for c in s:
            if ord(c) > 127:
                width += 2
            else:
                width += 1
        return width

    def refresh_line():
        import shutil
        term_width = shutil.get_terminal_size().columns

        if last_num_lines[0] > 1:
            for _ in range(last_num_lines[0] - 1):
                sys.stdout.write('\033[A\033[2K')

        sys.stdout.write('\r\033[2K')
        sys.stdout.write(prompt)
        sys.stdout.write(current_input)

        total_width = len(prompt) + get_display_width(current_input)
        last_num_lines[0] = max(1, (total_width + term_width - 1) // term_width)

        if cursor_pos < len(current_input):
            after_cursor = current_input[cursor_pos:]
            move_back = get_display_width(after_cursor)
            if move_back > 0:
                sys.stdout.write(f'\033[{move_back}D')
        sys.stdout.flush()

    try:
        tty.setraw(fd)
        sys.stdout.write(prompt)
        sys.stdout.flush()

        while True:
            ch = sys.stdin.read(1)

            if ch == '\r' or ch == '\n':
                sys.stdout.write('\n')
                sys.stdout.flush()
                break

            elif ch == '\x03':
                sys.stdout.write('\n')
                raise EOFError

            elif ch == '\x04':
                if not current_input:
                    raise EOFError
                continue

            elif ch == '\x7f' or ch == '\x08':
                if cursor_pos > 0:
                    current_input = current_input[:cursor_pos-1] + current_input[cursor_pos:]
                    cursor_pos -= 1
                    refresh_line()

            elif ch == '\x1b':
                old_flags = fcntl.fcntl(fd, fcntl.F_GETFL)
                fcntl.fcntl(fd, fcntl.F_SETFL, old_flags | os.O_NONBLOCK)

                try:
                    ch2 = sys.stdin.read(1)
                except (IOError, BlockingIOError):
                    ch2 = None
                finally:
                    fcntl.fcntl(fd, fcntl.F_SETFL, old_flags)

                if ch2 is None or ch2 == '':
                    sys.stdout.write('\n')
                    raise KeyboardInterrupt

                if ch2 == '[':
                    ch3 = sys.stdin.read(1)
                    if ch3 == 'A':
                        history.set_current(current_input)
                        prev = history.previous()
                        if prev is not None:
                            current_input = prev
                            cursor_pos = len(current_input)
                            refresh_line()
                    elif ch3 == 'B':
                        next_cmd = history.next()
                        if next_cmd is not None:
                            current_input = next_cmd
                            cursor_pos = len(current_input)
                            refresh_line()
                    elif ch3 == 'C':
                        if cursor_pos < len(current_input):
                            cursor_pos += 1
                            refresh_line()
                    elif ch3 == 'D':
                        if cursor_pos > 0:
                            cursor_pos -= 1
                            refresh_line()
                    elif ch3 == '3':
                        sys.stdin.read(1)
                        if cursor_pos < len(current_input):
                            current_input = current_input[:cursor_pos] + current_input[cursor_pos+1:]
                            refresh_line()
                    elif ch3 == 'H':
                        cursor_pos = 0
                        refresh_line()
                    elif ch3 == 'F':
                        cursor_pos = len(current_input)
                        refresh_line()
                elif ch2 == 'O':
                    ch3 = sys.stdin.read(1)
                    if ch3 == 'C':
                        if cursor_pos < len(current_input):
                            cursor_pos += 1
                            refresh_line()
                    elif ch3 == 'D':
                        if cursor_pos > 0:
                            cursor_pos -= 1
                            refresh_line()

            elif ch == '\x01':
                cursor_pos = 0
                refresh_line()

            elif ch == '\x05':
                cursor_pos = len(current_input)
                refresh_line()

            elif ch == '\x0b':
                current_input = current_input[:cursor_pos]
                refresh_line()

            elif ch == '\x15':
                current_input = current_input[cursor_pos:]
                cursor_pos = 0
                refresh_line()

            elif ch == '\x17':
                pos = cursor_pos
                while pos > 0 and current_input[pos-1] == ' ':
                    pos -= 1
                while pos > 0 and current_input[pos-1] != ' ':
                    pos -= 1
                current_input = current_input[:pos] + current_input[cursor_pos:]
                cursor_pos = pos
                refresh_line()

            elif ch >= ' ':
                current_input = current_input[:cursor_pos] + ch + current_input[cursor_pos:]
                cursor_pos += 1
                refresh_line()

    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)

    return current_input
