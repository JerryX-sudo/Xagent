"""Tests for tools module."""

import sys
from pathlib import Path

# Ensure correct path
sys.path.insert(0, str(Path(__file__).parent.parent))

import tempfile

import pytest

from tools.base import BaseTool
from tools.bash import BashTool
from tools.edit import ReadFileTool
from tools.search import GlobTool, GrepTool, ListDirTool
from tools.python_repl import PythonREPLTool
from core.permission import PermissionManager


class TestBaseTool:
    """Tests for BaseTool class."""

    def test_to_openai_function(self):
        """Test converting tool to OpenAI format."""
        class TestTool(BaseTool):
            name = "test"
            description = "A test tool"
            parameters = {
                "type": "object",
                "properties": {"arg": {"type": "string"}},
            }

            def run(self, **kwargs):
                return "result"

        tool = TestTool()
        func = tool.to_openai_function()

        assert func["type"] == "function"
        assert func["function"]["name"] == "test"
        assert func["function"]["description"] == "A test tool"


class TestBashTool:
    """Tests for BashTool."""

    def test_simple_command(self):
        """Test executing a simple command."""
        tool = BashTool()
        result = tool.run(command="echo hello")
        assert "hello" in result

    def test_command_with_output(self):
        """Test command with output."""
        tool = BashTool()
        result = tool.run(command="pwd")
        assert "/" in result

    def test_forbidden_xagent(self):
        """Test that xagent command is forbidden."""
        tool = BashTool()
        result = tool.run(command="xagent --help")
        assert "recursive" in result.lower() or "forbidden" in result.lower()

    def test_dangerous_command_detection(self):
        """Test dangerous command detection."""
        tool = BashTool()
        assert tool._is_dangerous("rm -rf /") is True
        assert tool._is_dangerous("sudo apt install") is True
        assert tool._is_dangerous("echo hello | rm file") is True
        assert tool._is_dangerous("echo hello") is False
        assert tool._is_dangerous("ls -la") is False


class TestReadFileTool:
    """Tests for ReadFileTool."""

    def test_read_file(self, tmp_path):
        """Test reading a file."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("Hello, World!")

        tool = ReadFileTool()
        result = tool.run(file_path=str(test_file))
        assert "Hello, World!" in result

    def test_read_nonexistent(self):
        """Test reading nonexistent file."""
        tool = ReadFileTool()
        result = tool.run(file_path="/nonexistent/file.txt")
        assert "Error" in result or "not found" in result.lower()

    def test_read_with_line_range(self, tmp_path):
        """Test reading specific lines."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("line1\nline2\nline3\nline4\nline5")

        tool = ReadFileTool()
        result = tool.run(file_path=str(test_file), start_line=2, end_line=4)
        assert "line2" in result
        assert "line3" in result
        assert "line4" in result


class TestGlobTool:
    """Tests for GlobTool."""

    def test_find_files(self, tmp_path):
        """Test finding files by pattern."""
        (tmp_path / "test1.py").write_text("# test")
        (tmp_path / "test2.py").write_text("# test")
        (tmp_path / "test.txt").write_text("test")

        tool = GlobTool()
        result = tool.run(pattern="*.py", path=str(tmp_path))

        assert "test1.py" in result
        assert "test2.py" in result
        assert "test.txt" not in result


class TestGrepTool:
    """Tests for GrepTool."""

    def test_search_content(self, tmp_path):
        """Test searching file contents."""
        test_file = tmp_path / "test.py"
        test_file.write_text("def hello():\n    print('hello')\n\ndef world():\n    pass")

        tool = GrepTool()
        result = tool.run(pattern="def.*\\(\\)", path=str(tmp_path))

        assert "def hello()" in result
        assert "def world()" in result


class TestListDirTool:
    """Tests for ListDirTool."""

    def test_list_directory(self, tmp_path):
        """Test listing directory."""
        (tmp_path / "file1.txt").write_text("test")
        (tmp_path / "file2.py").write_text("test")
        (tmp_path / "subdir").mkdir()

        tool = ListDirTool()
        result = tool.run(path=str(tmp_path))

        assert "file1.txt" in result
        assert "file2.py" in result
        assert "subdir" in result


class TestPythonREPLTool:
    """Tests for PythonREPLTool."""

    def test_simple_expression(self):
        """Test simple expression evaluation."""
        tool = PythonREPLTool()
        result = tool.run(code="2 + 2")
        assert "4" in result

    def test_variable_persistence(self):
        """Test that variables persist."""
        tool = PythonREPLTool()
        tool.run(code="x = 10")
        result = tool.run(code="x * 2")
        assert "20" in result

    def test_print_output(self):
        """Test capturing print output."""
        tool = PythonREPLTool()
        result = tool.run(code="print('hello world')")
        assert "hello world" in result

    def test_error_handling(self):
        """Test error handling."""
        tool = PythonREPLTool()
        result = tool.run(code="1/0")
        assert "Error" in result or "ZeroDivision" in result

    def test_reset(self):
        """Test resetting namespace."""
        tool = PythonREPLTool()
        tool.run(code="x = 10")
        tool.reset()
        result = tool.run(code="x")
        assert "Error" in result or "NameError" in result
