"""Cross-platform terminal compatibility utilities."""

import os
import sys

# Platform detection
IS_WINDOWS = sys.platform == "win32"

# Try to import Unix-specific modules
if not IS_WINDOWS:
    import tty
    import termios
    import fcntl
    import select as _select

    def get_terminal_settings():
        """Get current terminal settings."""
        try:
            fd = sys.stdin.fileno()
            return termios.tcgetattr(fd)
        except Exception:
            return None

    def set_terminal_settings(settings):
        """Restore terminal settings."""
        if settings is None:
            return
        try:
            fd = sys.stdin.fileno()
            termios.tcsetattr(fd, termios.TCSADRAIN, settings)
        except Exception:
            pass

    def set_raw_mode():
        """Set terminal to raw mode for single char reads."""
        try:
            fd = sys.stdin.fileno()
            tty.setraw(fd)
        except Exception:
            pass

    def set_cbreak_mode():
        """Set terminal to cbreak mode (no echo, no line buffering)."""
        try:
            fd = sys.stdin.fileno()
            new_settings = termios.tcgetattr(fd)
            new_settings[3] = new_settings[3] & ~termios.ICANON & ~termios.ECHO
            termios.tcsetattr(fd, termios.TCSANOW, new_settings)
        except Exception:
            pass

    def reset_terminal():
        """Reset terminal to sane mode."""
        os.system('stty sane 2>/dev/null')

    def set_nonblocking(fd):
        """Set file descriptor to non-blocking mode. Returns old flags."""
        try:
            old_flags = fcntl.fcntl(fd, fcntl.F_GETFL)
            fcntl.fcntl(fd, fcntl.F_SETFL, old_flags | os.O_NONBLOCK)
            return old_flags
        except Exception:
            return None

    def restore_blocking(fd, old_flags):
        """Restore file descriptor blocking mode."""
        if old_flags is not None:
            try:
                fcntl.fcntl(fd, fcntl.F_SETFL, old_flags)
            except Exception:
                pass

    def select_stdin(timeout=0.1):
        """Check if stdin has data available. Returns True if data ready."""
        try:
            rlist, _, _ = _select.select([sys.stdin], [], [], timeout)
            return bool(rlist)
        except Exception:
            return False

    def read_char():
        """Read a single character from stdin."""
        try:
            return sys.stdin.read(1)
        except Exception:
            return None

else:
    # Windows implementation using msvcrt
    import msvcrt

    def get_terminal_settings():
        """Get current terminal settings (no-op on Windows)."""
        return None

    def set_terminal_settings(settings):
        """Restore terminal settings (no-op on Windows)."""
        pass

    def set_raw_mode():
        """Set terminal to raw mode (no-op on Windows, msvcrt handles this)."""
        pass

    def set_cbreak_mode():
        """Set terminal to cbreak mode (no-op on Windows)."""
        pass

    def reset_terminal():
        """Reset terminal to sane mode (no-op on Windows)."""
        pass

    def set_nonblocking(fd):
        """Set non-blocking mode (not applicable on Windows)."""
        return None

    def restore_blocking(fd, old_flags):
        """Restore blocking mode (not applicable on Windows)."""
        pass

    def select_stdin(timeout=0.1):
        """Check if stdin has data available."""
        return msvcrt.kbhit()

    def read_char():
        """Read a single character from stdin."""
        if msvcrt.kbhit():
            ch = msvcrt.getwch()
            return ch
        return None


def getch_with_timeout(timeout=0.1):
    """Read a character with timeout. Returns None if no input."""
    if IS_WINDOWS:
        import time
        start = time.time()
        while time.time() - start < timeout:
            if msvcrt.kbhit():
                return msvcrt.getwch()
            time.sleep(0.01)
        return None
    else:
        if select_stdin(timeout):
            return read_char()
        return None
