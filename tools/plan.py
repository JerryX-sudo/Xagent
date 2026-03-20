"""Planning tool for Xagent."""

from typing import Any

from tools.base import BaseTool
from memory.dynamic import DynamicMemory


class PlanTool(BaseTool):
    """Tool for creating and managing task plans."""

    name = "plan"
    description = "Create a plan with multiple tasks. Use this to break down complex requests into steps."
    parameters = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["create", "list", "complete", "update"],
                "description": "Action to perform: create (new plan), list (show tasks), complete (mark task done), update (change task status)",
            },
            "tasks": {
                "type": "array",
                "items": {"type": "string"},
                "description": "List of task descriptions (for 'create' action)",
            },
            "task_id": {
                "type": "string",
                "description": "Task ID to update (for 'complete' or 'update' action)",
            },
            "status": {
                "type": "string",
                "enum": ["pending", "in_progress", "completed", "failed"],
                "description": "New status (for 'update' action)",
            },
            "note": {
                "type": "string",
                "description": "Optional note to add to task",
            },
        },
        "required": ["action"],
    }

    def __init__(self, dynamic_memory: DynamicMemory):
        self.memory = dynamic_memory

    def run(self, **kwargs: Any) -> str:
        """Execute the plan action."""
        action = kwargs.get("action", "list")

        if action == "create":
            tasks = kwargs.get("tasks", [])
            if not tasks:
                return "Error: No tasks provided"

            # Clear existing tasks and create new plan
            self.memory.clear()
            created = []
            for desc in tasks:
                task = self.memory.add_task(desc)
                created.append(f"  [ ] {task.id}: {desc}")

            return f"Plan created with {len(created)} tasks:\n" + "\n".join(created)

        elif action == "list":
            tasks = self.memory.list_tasks()
            if not tasks:
                return "No active plan. Use 'create' to start a new plan."

            lines = ["Current Plan:"]
            for t in tasks:
                if t.status == "completed":
                    icon = "✓"
                elif t.status == "in_progress":
                    icon = "→"
                elif t.status == "failed":
                    icon = "✗"
                else:
                    icon = " "
                lines.append(f"  [{icon}] {t.id}: {t.description}")
                if t.notes:
                    for note in t.notes[-2:]:  # Show last 2 notes
                        lines.append(f"      └─ {note}")

            # Summary
            pending = len([t for t in tasks if t.status == "pending"])
            completed = len([t for t in tasks if t.status == "completed"])
            lines.append(f"\nProgress: {completed}/{len(tasks)} tasks completed")

            return "\n".join(lines)

        elif action == "complete":
            task_id = kwargs.get("task_id")
            if not task_id:
                return "Error: task_id required"

            note = kwargs.get("note")
            task = self.memory.update_task(task_id, status="completed", note=note)
            if not task:
                return f"Error: Task '{task_id}' not found"

            # Check if all tasks completed
            all_tasks = self.memory.list_tasks()
            pending = [t for t in all_tasks if t.status in ("pending", "in_progress")]

            result = f"✓ Completed: {task.description}"
            if not pending:
                result += "\n\n🎉 All tasks completed! Plan finished."
                # Compress memory after plan completion
                self._compress_completed_plan()
            else:
                result += f"\n\nRemaining: {len(pending)} task(s)"

            return result

        elif action == "update":
            task_id = kwargs.get("task_id")
            status = kwargs.get("status")
            note = kwargs.get("note")

            if not task_id:
                return "Error: task_id required"

            task = self.memory.update_task(task_id, status=status, note=note)
            if not task:
                return f"Error: Task '{task_id}' not found"

            return f"Updated {task_id}: status={task.status}"

        else:
            return f"Error: Unknown action '{action}'"

    def _compress_completed_plan(self) -> None:
        """Compress completed plan to save context."""
        tasks = self.memory.list_tasks()
        if not tasks:
            return

        # Store summary in context instead of full task list
        completed_count = len([t for t in tasks if t.status == "completed"])
        summary = f"Completed plan with {completed_count} tasks"

        # Clear tasks but keep summary
        self.memory._tasks.clear()
        self.memory.set_context("last_plan_summary", summary)
