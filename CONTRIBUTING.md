# Contributing to Xagent

Thank you for considering contributing to Xagent!

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [How Can I Contribute?](#how-can-i-contribute)
- [Development Setup](#development-setup)
- [Style Guidelines](#style-guidelines)
- [Pull Request Process](#pull-request-process)

## Code of Conduct

This project and everyone participating in it is governed by our Code of Conduct. By participating, you are expected to uphold this code. Please be respectful and considerate in all interactions.

## Getting Started

1. Fork the repository on GitHub
2. Clone your fork locally
3. Set up your development environment (see below)
4. Create a branch for your changes
5. Make your changes
6. Push to your fork and submit a pull request

## How Can I Contribute?

### Reporting Bugs

Before creating bug reports, please check existing issues to avoid duplicates. When you create a bug report, include:

- A clear and descriptive title
- Steps to reproduce the issue
- Expected behavior vs actual behavior
- System information (OS, Python version)
- Relevant logs or error messages

### Suggesting Enhancements

Enhancement suggestions are welcome! Please provide:

- A clear and descriptive title
- Detailed description of the proposed enhancement
- Use cases and examples

### Creating Tools/Plugins

When creating a tool:

1. Follow the `BaseTool` interface
2. Include docstrings
3. Add tests for your tool

Example tool structure:

```python
from tools.base import BaseTool

class MyTool(BaseTool):
    """Brief description of what the tool does."""

    name = "my_tool"
    description = "Detailed description for the AI model"
    parameters = {
        "type": "object",
        "properties": {
            "param1": {
                "type": "string",
                "description": "What this parameter does"
            }
        },
        "required": ["param1"]
    }

    def run(self, **kwargs):
        """Execute the tool logic."""
        # Implementation here
        return result
```

## Development Setup

### Prerequisites

- Python 3.12 or higher
- Git
- uv (recommended) or pip

### Setup Steps

```bash
# Clone your fork
git clone https://github.com/YOUR_USERNAME/Xagent.git
cd Xagent

# Add upstream remote
git remote add upstream https://github.com/JerryX-sudo/Xagent.git

# Create virtual environment and install dependencies
uv venv
source .venv/bin/activate
uv pip install -e ".[dev]"
```

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=. --cov-report=term-missing

# Run specific test
pytest tests/test_tools.py::TestBashTool
```

## Style Guidelines

### Python Style

We follow PEP 8:

```bash
# Format code
black .

# Check style
ruff check .

# Type checking
mypy .
```

### Commit Messages

Follow conventional commits:

- `feat:` New feature
- `fix:` Bug fix
- `docs:` Documentation changes
- `refactor:` Code refactoring
- `test:` Test additions or changes
- `chore:` Maintenance tasks

Examples:
```
feat: add web scraping tool
fix: handle API timeout in OpenAI client
docs: update plugin development guide
```

### Code Guidelines

1. Use descriptive variable and function names
2. Add type hints to function signatures
3. Include docstrings for public functions and classes
4. Use appropriate exception handling

## Pull Request Process

1. Update your fork:
   ```bash
   git checkout main
   git fetch upstream
   git merge upstream/main
   ```

2. Create a feature branch:
   ```bash
   git checkout -b feature/your-feature-name
   ```

3. Make your changes, add tests, update documentation

4. Test your changes:
   ```bash
   pytest
   black .
   ruff check .
   ```

5. Commit and push:
   ```bash
   git add .
   git commit -m "feat: add amazing feature"
   git push origin feature/your-feature-name
   ```

6. Create Pull Request on GitHub

### Pull Request Checklist

- [ ] Tests pass locally
- [ ] Code follows style guidelines
- [ ] Documentation updated if needed
- [ ] No new warnings

## Getting Help

If you need help:

1. Check the [README](README.md)
2. Search [existing issues](https://github.com/JerryX-sudo/Xagent/issues)
3. Open a new issue

Thank you for contributing!
