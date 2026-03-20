"""Tool registry and plugin system for Xagent."""

import importlib.util
from pathlib import Path
from typing import Any

from core.config import Config
from core.permission import PermissionManager
from tools.base import BaseTool
from tools.bash import BashTool
from tools.ask_human import AskHumanTool
from tools.final_answer import FinalAnswerTool
from tools.memory_tool import MemoryTool
from tools.edit import EditTool, WriteFileTool, ReadFileTool
from tools.search import GlobTool, GrepTool, ListDirTool
from tools.web import WebFetchTool, WebSearchTool
from tools.git import GitTool, GitStatusTool, GitDiffTool, GitLogTool
from tools.python_repl import PythonREPLTool
from tools.plan import PlanTool
from utils.output import OutputManager


class ToolRegistry:
    """Registry for managing tools and plugins."""

    def __init__(
        self,
        config: Config,
        dynamic_memory=None,
        permission_manager=None,
        output_manager=None,
    ):
        self.config = config
        self.dynamic_memory = dynamic_memory
        self.permission_manager = permission_manager or PermissionManager()
        self.output_manager = output_manager or OutputManager()
        self._tools: dict[str, BaseTool] = {}
        self._register_builtin_tools()

    def _register_builtin_tools(self) -> None:
        """Register built-in tools."""
        self.register(BashTool(
            self.config.dangerous_commands,
            self.permission_manager,
            self.output_manager,
        ))
        self.register(AskHumanTool())
        self.register(FinalAnswerTool())
        self.register(EditTool(self.permission_manager))
        self.register(WriteFileTool(self.permission_manager))
        self.register(ReadFileTool())
        self.register(GlobTool())
        self.register(GrepTool())
        self.register(ListDirTool())
        self.register(WebFetchTool())
        self.register(WebSearchTool())
        self.register(GitTool(self.permission_manager))
        self.register(GitStatusTool())
        self.register(GitDiffTool())
        self.register(GitLogTool())
        self.register(PythonREPLTool(self.permission_manager))
        if self.dynamic_memory:
            self.register(MemoryTool(self.dynamic_memory))
            self.register(PlanTool(self.dynamic_memory))

    def register(self, tool: BaseTool) -> None:
        """Register a tool."""
        self._tools[tool.name] = tool

    def unregister(self, name: str) -> None:
        """Unregister a tool by name."""
        if name in self._tools:
            del self._tools[name]

    def get(self, name: str) -> BaseTool | None:
        """Get a tool by name."""
        return self._tools.get(name)

    def list_tools(self) -> list[str]:
        """List all registered tool names."""
        return list(self._tools.keys())

    def get_all(self) -> dict[str, BaseTool]:
        """Get all registered tools."""
        return self._tools.copy()

    def to_openai_functions(self) -> list[dict[str, Any]]:
        """Convert all tools to OpenAI function calling format."""
        return [tool.to_openai_function() for tool in self._tools.values()]

    def load_plugins(self) -> int:
        """Load plugins from ~/.xagent/plugins/. Returns count of loaded plugins."""
        plugins_dir = Config.get_config_dir() / "plugins"
        if not plugins_dir.exists():
            plugins_dir.mkdir(parents=True, exist_ok=True)
            return 0

        count = 0
        for plugin_file in plugins_dir.glob("*.py"):
            if plugin_file.name.startswith("_"):
                continue

            try:
                spec = importlib.util.spec_from_file_location(
                    plugin_file.stem, plugin_file
                )
                if spec and spec.loader:
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)

                    # Find and register BaseTool subclasses
                    for attr_name in dir(module):
                        attr = getattr(module, attr_name)
                        if (
                            isinstance(attr, type)
                            and issubclass(attr, BaseTool)
                            and attr is not BaseTool
                            and hasattr(attr, "name")
                            and attr.name
                        ):
                            tool = attr()
                            self.register(tool)
                            count += 1

            except Exception as e:
                print(f"Warning: Failed to load plugin {plugin_file.name}: {e}")

        return count

    def execute(self, name: str, **kwargs: Any) -> str:
        """Execute a tool by name with given arguments."""
        tool = self.get(name)
        if not tool:
            return f"Error: Tool '{name}' not found"
        return tool.run(**kwargs)
