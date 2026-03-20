# Xagent

A lightweight terminal Agent framework - small but powerful.

## Installation

```bash
pip install git+https://github.com/yourusername/xagent.git
```

## Quick Start

### Option 1: Environment Variables (Recommended)

```bash
# Set your API credentials
export XAGENT_API_KEY="your-api-key"
export XAGENT_MODEL="gpt-4o"  # or claude-sonnet-4-20250514

# Optional: custom endpoint
export XAGENT_BASE_URL="https://api.openai.com/v1"

# Run
xagent
```

### Option 2: Interactive Setup

Just run `xagent` - it will prompt you for:
1. API Key
2. Base URL (optional, press Enter for default)
3. Model name

The connection will be tested before starting. If it fails, you can retry with different settings.

```bash
$ xagent

╭──────────── Xagent Setup ────────────╮
│ Environment variables not found.     │
│ Please enter your configuration.     │
╰──────────────────────────────────────╯

API Key: ********
Base URL:
Model [gpt-4o]:

Testing connection...
✓ Connection successful!
```

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `XAGENT_API_KEY` | Yes | Your API key |
| `XAGENT_MODEL` | No | Model name (default: gpt-4o) |
| `XAGENT_BASE_URL` | No | Custom API endpoint |

**Supported models:**
- OpenAI: `gpt-4o`, `gpt-4-turbo`, `gpt-3.5-turbo`
- Anthropic: `claude-sonnet-4-20250514`, `claude-opus-4-20250514`
- Any OpenAI-compatible endpoint via `XAGENT_BASE_URL`

## Usage

### Interactive Mode

```bash
xagent
```

### Single Question

```bash
xagent ask "What files are in this directory?"
```

### Update

```bash
xagent update
```

## Commands

| Command | Description |
|---------|-------------|
| `/help` | Show help |
| `/clear` | Clear conversation |
| `/exit` | Exit xagent |
| `/memory` | View/manage persistent memory |
| `/history` | Show conversation history |
| `/save [name]` | Save session |
| `/load <name>` | Load session |
| `/export [name]` | Export to markdown |
| `/cache` | View/clear cache |
| `/tools` | List available tools |
| `/theme [name]` | View/change theme |
| `/permissions` | Manage auto-approve |

## Built-in Tools

| Tool | Description |
|------|-------------|
| `bash` | Execute shell commands |
| `python` | Execute Python code |
| `edit` | Edit files with diff preview |
| `write_file` | Create/overwrite files |
| `read_file` | Read file contents |
| `glob` | Find files by pattern |
| `grep` | Search file contents |
| `ls` | List directory |
| `git` | Git operations |
| `git_status` | Quick git status |
| `git_diff` | View git diff |
| `git_log` | View git history |
| `web_search` | Search the web |
| `web_fetch` | Fetch web page content |
| `ask_human` | Ask user questions |
| `memory` | Manage session memory |

## Features

- **Multi-model**: OpenAI, Anthropic, any OpenAI-compatible API
- **17 Built-in Tools**: Shell, Python, files, git, web, and more
- **Permission Control**: Approve/deny actions with diff preview
- **Arrow Key History**: ↑↓ to navigate command history
- **Session Management**: Save, load, and export conversations
- **Request Caching**: Save tokens with intelligent caching
- **Plugin System**: Add custom tools in `~/.xagent/plugins/`
- **Themes**: Customizable color schemes

## Keyboard Shortcuts

| Key | Action |
|-----|--------|
| ↑/↓ | Navigate history |
| Ctrl+A | Move to line start |
| Ctrl+E | Move to line end |
| Ctrl+K | Delete to end of line |
| Ctrl+U | Delete to start of line |
| Ctrl+W | Delete word |
| Ctrl+C | Cancel current input |

## Plugins

Create custom tools in `~/.xagent/plugins/`:

```python
# ~/.xagent/plugins/my_tool.py
from tools.base import BaseTool

class MyTool(BaseTool):
    name = "my_tool"
    description = "Does something custom"
    parameters = {
        "type": "object",
        "properties": {
            "input": {"type": "string"},
        },
        "required": ["input"],
    }

    def run(self, **kwargs):
        return f"Result: {kwargs.get('input')}"
```

## File Locations

```
~/.xagent/
├── memory.md        # Persistent memory
├── history          # Command history
├── cache/           # Request cache
├── sessions/        # Saved sessions
├── exports/         # Exported conversations
├── plugins/         # Custom tools
└── logs/            # Debug logs
```

## Development

```bash
# Clone and install
git clone https://github.com/yourusername/xagent.git
cd xagent
pip install -e ".[dev]"

# Run tests
pytest tests/ -v
```

See [DEVELOPMENT.md](DEVELOPMENT.md) for architecture details.

## License

Apache-2.0
