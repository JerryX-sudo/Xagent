"""Memory management tool for Xagent."""

from typing import Any

from tools.base import BaseTool


class MemoryTool(BaseTool):
    """Tool for managing dynamic memory (tasks and context)."""

    name = "memory"
    description = "Manage your working memory. Use this to track tasks, store context, and organize your work during the session."
    parameters = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["add_task", "update_task", "list_tasks", "set_context", "get_context", "summarize"],
                "description": "The action to perform",
            },
            "task_description": {
                "type": "string",
                "description": "Description for a new task (used with add_task)",
            },
            "task_id": {
                "type": "string",
                "description": "Task ID (used with update_task)",
            },
            "status": {
                "type": "string",
                "enum": ["pending", "in_progress", "completed", "failed"],
                "description": "New status for the task (used with update_task)",
            },
            "note": {
                "type": "string",
                "description": "Note to add to the task (used with update_task)",
            },
            "key": {
                "type": "string",
                "description": "Context key (used with set_context/get_context)",
            },
            "value": {
                "type": "string",
                "description": "Context value (used with set_context)",
            },
        },
        "required": ["action"],
    }

    def __init__(self, dynamic_memory):
        self.memory = dynamic_memory

    def run(self, **kwargs: Any) -> str:
        """Execute memory action."""
        action = kwargs.get("action", "")

        if action == "add_task":
            desc = kwargs.get("task_description", "")
            if not desc:
                return "Error: task_description required"
            task = self.memory.add_task(desc)
            return f"Created task {task.id}: {task.description}"

        elif action == "update_task":
            task_id = kwargs.get("task_id", "")
            if not task_id:
                return "Error: task_id required"
            task = self.memory.update_task(
                task_id,
                status=kwargs.get("status"),
                note=kwargs.get("note"),
            )
            if not task:
                return f"Error: Task {task_id} not found"
            return f"Updated task {task.id}: status={task.status}"

        elif action == "list_tasks":
            tasks = self.memory.list_tasks()
            if not tasks:
                return "No tasks"
            lines = []
            for t in tasks:
                lines.append(f"- {t.id}: [{t.status}] {t.description}")
            return "\n".join(lines)

        elif action == "set_context":
            key = kwargs.get("key", "")
            value = kwargs.get("value", "")
            if not key:
                return "Error: key required"
            self.memory.set_context(key, value)
            return f"Set context: {key} = {value}"

        elif action == "get_context":
            key = kwargs.get("key", "")
            if not key:
                return "Error: key required"
            value = self.memory.get_context(key)
            return f"{key} = {value}" if value else f"{key} not found"

        elif action == "summarize":
            return self.memory.summarize()

        else:
            return f"Unknown action: {action}"
