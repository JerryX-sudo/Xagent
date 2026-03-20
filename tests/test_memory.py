"""Tests for memory module."""

import sys
from pathlib import Path

# Ensure correct path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest

from memory.dynamic import DynamicMemory, Task
from memory.static import StaticMemory
from core.config import Config


class TestDynamicMemory:
    """Tests for DynamicMemory class."""

    def test_add_task(self):
        """Test adding a task."""
        memory = DynamicMemory()
        task = memory.add_task("Test task")

        assert task.id == "task_1"
        assert task.description == "Test task"
        assert task.status == "pending"

    def test_update_task(self):
        """Test updating a task."""
        memory = DynamicMemory()
        task = memory.add_task("Test task")

        updated = memory.update_task(task.id, status="in_progress")
        assert updated.status == "in_progress"

        updated = memory.update_task(task.id, note="Working on it")
        assert "Working on it" in updated.notes

    def test_list_tasks(self):
        """Test listing tasks."""
        memory = DynamicMemory()
        memory.add_task("Task 1")
        memory.add_task("Task 2")
        memory.add_task("Task 3")

        all_tasks = memory.list_tasks()
        assert len(all_tasks) == 3

        memory.update_task("task_1", status="completed")
        completed = memory.list_tasks(status="completed")
        assert len(completed) == 1

    def test_context(self):
        """Test context storage."""
        memory = DynamicMemory()
        memory.set_context("key1", "value1")
        memory.set_context("key2", 42)

        assert memory.get_context("key1") == "value1"
        assert memory.get_context("key2") == 42
        assert memory.get_context("nonexistent") is None

    def test_clear(self):
        """Test clearing memory."""
        memory = DynamicMemory()
        memory.add_task("Task")
        memory.set_context("key", "value")

        memory.clear()
        assert len(memory.list_tasks()) == 0
        assert memory.get_context("key") is None

    def test_summarize(self):
        """Test generating summary."""
        memory = DynamicMemory()
        memory.add_task("Task 1")
        memory.add_task("Task 2")
        memory.update_task("task_1", status="in_progress")
        memory.set_context("current_file", "test.py")

        summary = memory.summarize()
        assert "Tasks" in summary
        assert "In Progress" in summary
        assert "current_file" in summary


class TestStaticMemory:
    """Tests for StaticMemory class."""

    def test_read_write(self, tmp_path, monkeypatch):
        """Test reading and writing memory."""
        monkeypatch.setattr(Config, "get_config_dir", lambda: tmp_path)

        memory = StaticMemory()
        memory.write("# Test Memory\n\nSome content")

        content = memory.read()
        assert "Test Memory" in content
        assert "Some content" in content

    def test_append(self, tmp_path, monkeypatch):
        """Test appending to memory."""
        monkeypatch.setattr(Config, "get_config_dir", lambda: tmp_path)

        memory = StaticMemory()
        memory.append("First entry")
        memory.append("Second entry")

        content = memory.read()
        assert "First entry" in content
        assert "Second entry" in content

    def test_search(self, tmp_path, monkeypatch):
        """Test searching memory."""
        monkeypatch.setattr(Config, "get_config_dir", lambda: tmp_path)

        memory = StaticMemory()
        memory.write("# Memory\n\nPython is great\nJavaScript too\nPython again")

        results = memory.search("Python")
        assert len(results) == 2

    def test_clear(self, tmp_path, monkeypatch):
        """Test clearing memory."""
        monkeypatch.setattr(Config, "get_config_dir", lambda: tmp_path)

        memory = StaticMemory()
        memory.append("Some content")
        memory.clear()

        content = memory.read()
        assert "Some content" not in content
        assert "Xagent Memory" in content

    def test_sections(self, tmp_path, monkeypatch):
        """Test section management."""
        monkeypatch.setattr(Config, "get_config_dir", lambda: tmp_path)

        memory = StaticMemory()
        memory.append("Entry 1")
        memory.append("Entry 2")

        sections = memory.get_sections()
        assert len(sections) >= 2
