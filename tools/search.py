"""File search tools for Xagent."""

import fnmatch
import re
from pathlib import Path
from typing import Any

from tools.base import BaseTool


class GlobTool(BaseTool):
    """Tool for finding files by pattern."""

    name = "glob"
    description = "Find files matching a glob pattern. Use this to locate files in the project."
    parameters = {
        "type": "object",
        "properties": {
            "pattern": {
                "type": "string",
                "description": "Glob pattern (e.g., '**/*.py', 'src/**/*.js')",
            },
            "path": {
                "type": "string",
                "description": "Directory to search in (default: current directory)",
            },
            "max_results": {
                "type": "integer",
                "description": "Maximum number of results (default: 50)",
            },
        },
        "required": ["pattern"],
    }

    def run(self, **kwargs: Any) -> str:
        """Find files matching pattern."""
        pattern = kwargs.get("pattern", "")
        path = kwargs.get("path", ".")
        max_results = kwargs.get("max_results", 50)

        if not pattern:
            return "Error: pattern required"

        base_path = Path(path).expanduser().resolve()
        if not base_path.exists():
            return f"Error: Path not found: {base_path}"

        try:
            matches = list(base_path.glob(pattern))[:max_results]

            if not matches:
                return f"No files matching '{pattern}'"

            # Format output
            lines = [f"Found {len(matches)} file(s):"]
            for match in sorted(matches):
                try:
                    rel_path = match.relative_to(base_path)
                except ValueError:
                    rel_path = match
                lines.append(f"  {rel_path}")

            if len(matches) == max_results:
                lines.append(f"  ... (limited to {max_results} results)")

            return "\n".join(lines)

        except Exception as e:
            return f"Error: {e}"


class GrepTool(BaseTool):
    """Tool for searching file contents."""

    name = "grep"
    description = "Search for text in files. Returns matching lines with context."
    parameters = {
        "type": "object",
        "properties": {
            "pattern": {
                "type": "string",
                "description": "Text or regex pattern to search for",
            },
            "path": {
                "type": "string",
                "description": "File or directory to search in",
            },
            "file_pattern": {
                "type": "string",
                "description": "Glob pattern to filter files (e.g., '*.py')",
            },
            "ignore_case": {
                "type": "boolean",
                "description": "Case-insensitive search (default: false)",
            },
            "context_lines": {
                "type": "integer",
                "description": "Lines of context before/after match (default: 0)",
            },
            "max_results": {
                "type": "integer",
                "description": "Maximum matches to return (default: 50)",
            },
        },
        "required": ["pattern", "path"],
    }

    def run(self, **kwargs: Any) -> str:
        """Search for pattern in files."""
        pattern = kwargs.get("pattern", "")
        path = kwargs.get("path", ".")
        file_pattern = kwargs.get("file_pattern", "*")
        ignore_case = kwargs.get("ignore_case", False)
        context_lines = kwargs.get("context_lines", 0)
        max_results = kwargs.get("max_results", 50)

        if not pattern:
            return "Error: pattern required"

        base_path = Path(path).expanduser().resolve()
        if not base_path.exists():
            return f"Error: Path not found: {base_path}"

        flags = re.IGNORECASE if ignore_case else 0
        try:
            regex = re.compile(pattern, flags)
        except re.error as e:
            return f"Error: Invalid regex: {e}"

        results = []
        files_searched = 0

        # Get files to search
        if base_path.is_file():
            files = [base_path]
        else:
            files = list(base_path.rglob(file_pattern))

        for file_path in files:
            if not file_path.is_file():
                continue

            # Skip binary and hidden files
            if file_path.name.startswith('.'):
                continue

            files_searched += 1

            try:
                content = file_path.read_text(errors='ignore')
                lines = content.split('\n')

                for i, line in enumerate(lines):
                    if regex.search(line):
                        # Get context
                        start = max(0, i - context_lines)
                        end = min(len(lines), i + context_lines + 1)

                        context = []
                        for j in range(start, end):
                            prefix = ">" if j == i else " "
                            context.append(f"{prefix} {j+1:4d} │ {lines[j]}")

                        try:
                            rel_path = file_path.relative_to(base_path.parent if base_path.is_file() else base_path)
                        except ValueError:
                            rel_path = file_path

                        results.append({
                            "file": str(rel_path),
                            "line": i + 1,
                            "context": "\n".join(context),
                        })

                        if len(results) >= max_results:
                            break

            except Exception:
                continue

            if len(results) >= max_results:
                break

        if not results:
            return f"No matches for '{pattern}' in {files_searched} files"

        # Format output
        output = [f"Found {len(results)} match(es) in {files_searched} files:"]
        for r in results:
            output.append(f"\n{r['file']}:{r['line']}")
            output.append(r['context'])

        if len(results) == max_results:
            output.append(f"\n... (limited to {max_results} results)")

        return "\n".join(output)


class ListDirTool(BaseTool):
    """Tool for listing directory contents."""

    name = "ls"
    description = "List directory contents with details."
    parameters = {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "Directory to list (default: current directory)",
            },
            "all": {
                "type": "boolean",
                "description": "Include hidden files (default: false)",
            },
            "long": {
                "type": "boolean",
                "description": "Long format with details (default: false)",
            },
        },
    }

    def run(self, **kwargs: Any) -> str:
        """List directory contents."""
        path = kwargs.get("path", ".")
        show_all = kwargs.get("all", False)
        long_format = kwargs.get("long", False)

        dir_path = Path(path).expanduser().resolve()
        if not dir_path.exists():
            return f"Error: Path not found: {dir_path}"
        if not dir_path.is_dir():
            return f"Error: Not a directory: {dir_path}"

        try:
            entries = sorted(dir_path.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower()))

            if not show_all:
                entries = [e for e in entries if not e.name.startswith('.')]

            if not entries:
                return "(empty directory)"

            if long_format:
                lines = []
                for entry in entries:
                    stat = entry.stat()
                    size = stat.st_size
                    if size < 1024:
                        size_str = f"{size}B"
                    elif size < 1024 * 1024:
                        size_str = f"{size // 1024}K"
                    else:
                        size_str = f"{size // (1024 * 1024)}M"

                    type_char = "d" if entry.is_dir() else "-"
                    name = entry.name + ("/" if entry.is_dir() else "")
                    lines.append(f"{type_char} {size_str:>6} {name}")
                return "\n".join(lines)
            else:
                names = []
                for entry in entries:
                    name = entry.name + ("/" if entry.is_dir() else "")
                    names.append(name)
                return "  ".join(names)

        except Exception as e:
            return f"Error: {e}"
