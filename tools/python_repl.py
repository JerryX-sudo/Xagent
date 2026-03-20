"""Python REPL tool for Xagent."""

import sys
import io
import traceback
from typing import Any
from contextlib import redirect_stdout, redirect_stderr

from tools.base import BaseTool
from core.permission import PermissionManager


class PythonREPLTool(BaseTool):
    """Tool for executing Python code."""

    name = "python"
    description = "Execute Python code and return the result. Use for calculations, data processing, or testing code snippets."
    parameters = {
        "type": "object",
        "properties": {
            "code": {
                "type": "string",
                "description": "Python code to execute",
            },
        },
        "required": ["code"],
    }

    def __init__(self, permission_manager: PermissionManager | None = None):
        self.permission_manager = permission_manager or PermissionManager()
        # Shared namespace for persistent state
        self._namespace: dict[str, Any] = {
            "__builtins__": __builtins__,
            "__name__": "__xagent_repl__",
        }

    def _is_dangerous(self, code: str) -> bool:
        """Check if code contains dangerous operations."""
        dangerous_patterns = [
            "os.system", "subprocess", "eval(", "exec(",
            "open(", "__import__", "importlib",
            "shutil.rmtree", "os.remove", "os.unlink",
            "sys.exit", "quit(", "exit(",
        ]
        code_lower = code.lower()
        return any(p in code_lower for p in dangerous_patterns)

    def run(self, **kwargs: Any) -> str:
        """Execute Python code."""
        code = kwargs.get("code", "")

        if not code:
            return "Error: code required"

        # Check for dangerous code
        if self._is_dangerous(code):
            if not self.permission_manager.request_permission(
                tool_name="python",
                action_description="Execute potentially dangerous Python code",
                details=f"Code:\n{code[:500]}",
            ):
                return "Python execution cancelled by user"

        # Capture output
        stdout_capture = io.StringIO()
        stderr_capture = io.StringIO()

        try:
            with redirect_stdout(stdout_capture), redirect_stderr(stderr_capture):
                # Try eval first (for expressions)
                try:
                    result = eval(code, self._namespace)
                except SyntaxError:
                    # Fall back to exec for statements
                    exec(code, self._namespace)
                    result = None

            stdout_output = stdout_capture.getvalue()
            stderr_output = stderr_capture.getvalue()

            output_parts = []

            if result is not None:
                output_parts.append(f"Result: {repr(result)}")

            if stdout_output:
                output_parts.append(f"Output:\n{stdout_output.rstrip()}")

            if stderr_output:
                output_parts.append(f"Stderr:\n{stderr_output.rstrip()}")

            return "\n".join(output_parts) if output_parts else "(no output)"

        except Exception as e:
            tb = traceback.format_exc()
            # Simplify traceback
            lines = tb.split('\n')
            # Remove internal frames
            simplified = []
            skip_next = False
            for line in lines:
                if '<string>' in line or '__xagent_repl__' in line:
                    simplified.append(line)
                    skip_next = False
                elif line.startswith('Traceback') or line.startswith('  File'):
                    if '__xagent_repl__' in line or '<string>' in line:
                        simplified.append(line)
                else:
                    simplified.append(line)

            return f"Error:\n{e}\n\n{chr(10).join(simplified[-5:])}"

    def reset(self) -> None:
        """Reset the namespace (clear all variables)."""
        self._namespace = {
            "__builtins__": __builtins__,
            "__name__": "__xagent_repl__",
        }

    def get_variables(self) -> dict[str, Any]:
        """Get all user-defined variables."""
        return {
            k: v for k, v in self._namespace.items()
            if not k.startswith('_')
        }
