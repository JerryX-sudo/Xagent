"""Diff display utilities for Xagent."""

import difflib
from rich.console import Console
from rich.text import Text
from rich.panel import Panel


def generate_diff(old_content: str, new_content: str, filename: str = "") -> list[str]:
    """Generate unified diff lines."""
    old_lines = old_content.splitlines(keepends=True)
    new_lines = new_content.splitlines(keepends=True)

    diff = difflib.unified_diff(
        old_lines,
        new_lines,
        fromfile=f"a/{filename}" if filename else "original",
        tofile=f"b/{filename}" if filename else "modified",
        lineterm="",
    )
    return list(diff)


def print_diff(
    old_content: str,
    new_content: str,
    filename: str = "",
    console: Console | None = None,
    context_lines: int = 3,
) -> None:
    """Print a colorized diff to the console.

    Args:
        old_content: Original content
        new_content: New content
        filename: Optional filename for header
        console: Rich console instance
        context_lines: Number of context lines around changes
    """
    if console is None:
        console = Console()

    diff_lines = generate_diff(old_content, new_content, filename)

    if not diff_lines:
        console.print("[dim]No changes[/dim]")
        return

    text = Text()

    for line in diff_lines:
        line = line.rstrip('\n')

        if line.startswith('+++') or line.startswith('---'):
            # File headers
            text.append(line + "\n", style="bold")
        elif line.startswith('@@'):
            # Hunk headers
            text.append(line + "\n", style="cyan")
        elif line.startswith('+'):
            # Added lines
            text.append(line + "\n", style="green")
        elif line.startswith('-'):
            # Removed lines
            text.append(line + "\n", style="red")
        else:
            # Context lines
            text.append(line + "\n", style="dim")

    console.print(Panel(
        text,
        title=f"[bold]Changes: {filename}[/bold]" if filename else "[bold]Changes[/bold]",
        border_style="blue",
    ))


def print_inline_diff(
    old_content: str,
    new_content: str,
    filename: str = "",
    console: Console | None = None,
) -> None:
    """Print side-by-side inline diff showing only changed lines.

    Args:
        old_content: Original content
        new_content: New content
        filename: Optional filename for header
        console: Rich console instance
    """
    if console is None:
        console = Console()

    old_lines = old_content.splitlines()
    new_lines = new_content.splitlines()

    matcher = difflib.SequenceMatcher(None, old_lines, new_lines)

    text = Text()
    has_changes = False

    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == 'equal':
            # Show context (first and last line of equal block if large)
            if i2 - i1 > 6:
                for idx in range(i1, min(i1 + 2, i2)):
                    text.append(f"  {idx + 1:4d} │ {old_lines[idx]}\n", style="dim")
                text.append(f"       │ ... ({i2 - i1 - 4} lines unchanged) ...\n", style="dim italic")
                for idx in range(max(i2 - 2, i1 + 2), i2):
                    text.append(f"  {idx + 1:4d} │ {old_lines[idx]}\n", style="dim")
            else:
                for idx in range(i1, i2):
                    text.append(f"  {idx + 1:4d} │ {old_lines[idx]}\n", style="dim")

        elif tag == 'replace':
            has_changes = True
            for idx in range(i1, i2):
                text.append(f"- {idx + 1:4d} │ {old_lines[idx]}\n", style="red")
            for idx in range(j1, j2):
                text.append(f"+ {idx + 1:4d} │ {new_lines[idx]}\n", style="green")

        elif tag == 'delete':
            has_changes = True
            for idx in range(i1, i2):
                text.append(f"- {idx + 1:4d} │ {old_lines[idx]}\n", style="red")

        elif tag == 'insert':
            has_changes = True
            for idx in range(j1, j2):
                text.append(f"+ {idx + 1:4d} │ {new_lines[idx]}\n", style="green")

    if not has_changes:
        console.print("[dim]No changes[/dim]")
        return

    title = f"[bold]Diff: {filename}[/bold]" if filename else "[bold]Changes[/bold]"
    console.print(Panel(text, title=title, border_style="blue"))
