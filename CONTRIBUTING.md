# Contributing to Xagent

First off, thank you for considering contributing to Xagent! It's people like you that make Xagent such a great tool.

## 📋 Table of Contents

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

### 🐛 Reporting Bugs

Before creating bug reports, please check existing issues to avoid duplicates. When you create a bug report, include:

- A clear and descriptive title
- Steps to reproduce the issue
- Expected behavior
- Actual behavior
- System information (OS, Python version, etc.)
- Relevant logs or error messages

### 💡 Suggesting Enhancements

Enhancement suggestions are welcome! Please provide:

- A clear and descriptive title
- Detailed description of the proposed enhancement
- Use cases and examples
- Any relevant mockups or diagrams

### 🔧 Creating Tools/Plugins

We love new tools! When creating a tool:

1. Follow the `BaseTool` interface
2. Include comprehensive docstrings
3. Add tests for your tool
4. Update documentation

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

### 📝 Improving Documentation

Documentation improvements are always welcome:

- Fix typos or clarify existing documentation
- Add examples and use cases
- Translate documentation
- Improve code comments

## Development Setup

### Prerequisites

- Python 3.12 or higher
- Git
- A code editor (VS Code recommended)

### Setup Steps

```bash
# Clone your fork
git clone https://github.com/YOUR_USERNAME/xagent.git
cd xagent

# Add upstream remote
git remote add upstream https://github.com/ORIGINAL_OWNER/xagent.git

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install development dependencies
pip install -e ".[dev]"

# Install pre-commit hooks (optional but recommended)
pre-commit install
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

We use Black for code formatting and follow PEP 8:

```bash
# Format code
black .

# Check style
ruff check .

# Type checking
mypy .
```

### Commit Messages

Follow the conventional commits specification:

- `feat:` New feature
- `fix:` Bug fix
- `docs:` Documentation changes
- `style:` Code style changes (formatting, etc.)
- `refactor:` Code refactoring
- `test:` Test additions or changes
- `chore:` Maintenance tasks

Examples:
```
feat: add web scraping tool
fix: handle API timeout in OpenAI client
docs: update plugin development guide
```

### Code Style Guidelines

1. **Clear naming**: Use descriptive variable and function names
2. **Type hints**: Add type hints to function signatures
3. **Docstrings**: Include docstrings for all public functions and classes
4. **Error handling**: Use appropriate exception handling
5. **Logging**: Use the logger instead of print statements

Example:

```python
from typing import Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)

def process_data(
    input_data: str,
    options: Optional[Dict[str, Any]] = None
) -> str:
    """
    Process input data with optional configuration.
    
    Args:
        input_data: The data to process
        options: Optional configuration dictionary
        
    Returns:
        Processed data as string
        
    Raises:
        ValueError: If input_data is empty
    """
    if not input_data:
        raise ValueError("Input data cannot be empty")
        
    logger.debug(f"Processing data with options: {options}")
    
    # Processing logic here
    result = input_data.upper()
    
    return result
```

## Pull Request Process

1. **Update your fork**:
   ```bash
   git checkout main
   git fetch upstream
   git merge upstream/main
   ```

2. **Create a feature branch**:
   ```bash
   git checkout -b feature/your-feature-name
   ```

3. **Make your changes**:
   - Write code
   - Add tests
   - Update documentation

4. **Test your changes**:
   ```bash
   pytest
   black .
   ruff check .
   ```

5. **Commit your changes**:
   ```bash
   git add .
   git commit -m "feat: add amazing feature"
   ```

6. **Push to your fork**:
   ```bash
   git push origin feature/your-feature-name
   ```

7. **Create Pull Request**:
   - Go to the original repository
   - Click "New Pull Request"
   - Select your fork and branch
   - Fill in the PR template
   - Submit for review

### Pull Request Template

```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Testing
- [ ] Tests pass locally
- [ ] Added new tests
- [ ] Updated documentation

## Checklist
- [ ] Code follows style guidelines
- [ ] Self-review completed
- [ ] Comments added where necessary
- [ ] No new warnings
```

## 🎯 Development Tips

### Debugging

1. Enable debug logging:
   ```python
   import logging
   logging.basicConfig(level=logging.DEBUG)
   ```

2. Use the Python debugger:
   ```python
   import pdb; pdb.set_trace()
   ```

3. Test with different models and configurations

### Testing Tools

When developing tools, test them in isolation:

```python
from tools.my_tool import MyTool

tool = MyTool()
result = tool.run(param1="test")
print(result)
```

## 📚 Resources

- [Python Documentation](https://docs.python.org/3/)
- [Rich Documentation](https://rich.readthedocs.io/)
- [OpenAI API Reference](https://platform.openai.com/docs/api-reference)
- [Anthropic API Reference](https://docs.anthropic.com/claude/reference/getting-started-with-the-api)

## 🤝 Getting Help

If you need help:

1. Check the [documentation](README.md)
2. Search [existing issues](https://github.com/ORIGINAL_OWNER/xagent/issues)
3. Join our [discussions](https://github.com/ORIGINAL_OWNER/xagent/discussions)
4. Ask in the issue tracker

## 🙏 Recognition

Contributors will be recognized in:
- The project README
- Release notes
- Our contributors page

Thank you for contributing to Xagent! 🚀