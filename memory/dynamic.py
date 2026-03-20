"""Dynamic memory for in-session task tracking."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class Task:
    """A task being tracked in dynamic memory."""

    id: str
    description: str
    status: str = "pending"  # pending, in_progress, completed, failed
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    completed_at: str | None = None
    notes: list[str] = field(default_factory=list)


class DynamicMemory:
    """In-session dynamic memory for task tracking."""

    def __init__(self):
        self._tasks: dict[str, Task] = {}
        self._task_counter = 0
        self._context: dict[str, Any] = {}

    def add_task(self, description: str) -> Task:
        """Add a new task to track."""
        self._task_counter += 1
        task_id = f"task_{self._task_counter}"
        task = Task(id=task_id, description=description)
        self._tasks[task_id] = task
        return task

    def update_task(
        self,
        task_id: str,
        status: str | None = None,
        note: str | None = None,
    ) -> Task | None:
        """Update a task's status or add a note."""
        task = self._tasks.get(task_id)
        if not task:
            return None

        if status:
            task.status = status
            if status == "completed":
                task.completed_at = datetime.now().isoformat()

        if note:
            task.notes.append(note)

        return task

    def get_task(self, task_id: str) -> Task | None:
        """Get a task by ID."""
        return self._tasks.get(task_id)

    def list_tasks(self, status: str | None = None) -> list[Task]:
        """List all tasks, optionally filtered by status."""
        tasks = list(self._tasks.values())
        if status:
            tasks = [t for t in tasks if t.status == status]
        return tasks

    def set_context(self, key: str, value: Any) -> None:
        """Set a context value."""
        self._context[key] = value

    def get_context(self, key: str) -> Any:
        """Get a context value."""
        return self._context.get(key)

    def clear(self) -> None:
        """Clear all dynamic memory."""
        self._tasks.clear()
        self._context.clear()
        self._task_counter = 0

    def summarize(self) -> str:
        """Generate a summary of current dynamic memory state."""
        lines = []

        if self._tasks:
            lines.append("## Current Plan")
            for t in self._tasks.values():
                if t.status == "completed":
                    lines.append(f"  [✓] {t.id}: {t.description}")
                elif t.status == "in_progress":
                    lines.append(f"  [→] {t.id}: {t.description}")
                elif t.status == "failed":
                    lines.append(f"  [✗] {t.id}: {t.description}")
                else:
                    lines.append(f"  [ ] {t.id}: {t.description}")

            # Progress summary
            total = len(self._tasks)
            completed = len([t for t in self._tasks.values() if t.status == "completed"])
            lines.append(f"\nProgress: {completed}/{total} tasks")

        if self._context:
            lines.append("\n## Context")
            for key, value in self._context.items():
                lines.append(f"- {key}: {value}")

        return "\n".join(lines) if lines else "No active tasks or context."
