# Xagent Development Guide

## Architecture Overview

```
Xagent/
├── __init__.py              # Package metadata
├── __main__.py              # Entry: python -m xagent
├── cli.py                   # CLI main loop + commands
│
├── core/
│   ├── agent.py             # Agent loop (tool calling, streaming)
│   ├── config.py            # Configuration (env + yaml)
│   ├── session.py           # Conversation state
│   ├── cache.py             # Request caching (diskcache)
│   ├── permission.py        # Permission management (deny/allow/allow-task)
│   ├── prompts.py           # System prompts (centralized)
│   └── skills.py            # Skill system
│
├── llm/
│   ├── base.py              # Abstract LLM interface
│   ├── openai_client.py     # OpenAI/LiteLLM client
│   └── anthropic_client.py  # Anthropic client
│
├── tools/
│   ├── base.py              # BaseTool abstract class
│   ├── registry.py          # Tool registration + plugin loading
│   ├── bash.py              # Shell execution (with permission)
│   ├── edit.py              # File editing (with diff preview)
│   ├── ask_human.py         # Human interaction
│   ├── final_answer.py      # Task completion signal
│   └── memory_tool.py       # Dynamic memory management
│
├── memory/
│   ├── dynamic.py           # In-session task tracking
│   └── static.py            # Persistent memory (~/.xagent/memory.md)
│
├── utils/
│   ├── terminal.py          # Rich terminal UI
│   ├── select.py            # Interactive selection (↑/↓/Enter)
│   ├── output.py            # Collapsible output display
│   ├── diff.py              # Diff visualization (red/green)
│   └── logger.py            # Logging system
│
└── plugins/                 # Plugin directory
```

## Data Flow

```
User Input
    │
    ▼
┌─────────────────┐
│   CLI (cli.py)  │ ─── /commands ───► Handle locally
└────────┬────────┘
         │ text input
         ▼
┌─────────────────┐
│  Agent Loop     │◄────────────────────────────┐
│  (agent.py)     │                             │
└────────┬────────┘                             │
         │                                      │
         ▼                                      │
┌─────────────────┐                             │
│ Build Messages  │ ◄── Static Memory           │
│ + Dynamic Memory│ ◄── Dynamic Memory          │
└────────┬────────┘                             │
         │                                      │
         ▼                                      │
┌─────────────────┐     ┌──────────────┐        │
│   LLM Client    │────►│    Cache     │        │
│ (openai/claude) │◄────│  (diskcache) │        │
└────────┬────────┘     └──────────────┘        │
         │                                      │
         ▼                                      │
┌─────────────────┐                             │
│ Parse Response  │                             │
└────────┬────────┘                             │
         │                                      │
    ┌────┴────┐                                 │
    │         │                                 │
    ▼         ▼                                 │
 Content   Tool Calls                           │
    │         │                                 │
    ▼         ▼                                 │
 Print    ┌─────────────────┐                   │
          │  Tool Registry  │                   │
          └────────┬────────┘                   │
                   │                            │
          ┌────────┼────────┐                   │
          ▼        ▼        ▼                   │
       bash      edit    final_answer           │
          │        │           │                │
          │        ▼           ▼                │
          │   Permission    Return              │
          │     Check       Result              │
          │        │                            │
          └────────┴────────────────────────────┘
                        (loop continues)
```

## Core Components

### Agent (`core/agent.py`)

The agent implements a ReAct-style loop:

```python
def run(user_input, stream=True):
    session.add_message("user", user_input)

    for iteration in range(max_iterations):
        messages = get_messages_with_dynamic_memory()
        tools = registry.to_openai_functions()

        # Check cache (non-streaming only)
        if not stream and (cached := cache.get(...)):
            response = cached
        else:
            response = llm.chat_stream(messages, tools)

        if response.has_tool_calls:
            for tool_call in response.tool_calls:
                result = execute_tool(tool_call)
                if tool_call.name == "final_answer":
                    return result
                session.add_message("tool", result)
            continue  # Next iteration
        else:
            return response.content  # No tools, done
```

### Permission System (`core/permission.py`)

Three-tier permission model:
- **Deny**: Reject the action
- **Allow once**: Approve this action only
- **Allow for task**: Auto-approve similar actions until task ends

```python
# Interactive selection with arrow keys
options = [
    SelectOption("Deny", "deny", shortcut="n"),
    SelectOption("Allow once", "allow_once", shortcut="y"),
    SelectOption("Allow for task", "allow_task", shortcut="a"),
]
result = select_option(options, "Choose action")
```

### Tool System

Tools follow OpenAI function calling format:

```python
class MyTool(BaseTool):
    name = "my_tool"
    description = "What the tool does"
    parameters = {
        "type": "object",
        "properties": {
            "param": {"type": "string", "description": "..."},
        },
        "required": ["param"],
    }

    def run(self, **kwargs) -> str:
        return "result"
```

**Built-in tools:**

| Tool | Description | Permission |
|------|-------------|------------|
| `bash` | Execute shell commands | Required for dangerous commands |
| `edit` | Edit files (with diff) | Required |
| `write_file` | Create/overwrite files | Required |
| `read_file` | Read file contents | None |
| `ask_human` | Ask user questions | None |
| `memory` | Manage dynamic memory | None |
| `final_answer` | Complete task | None |

**Forbidden commands** (recursive call prevention):
- `xagent`, `python -m xagent`

### Memory System

**Dynamic Memory** (in-session):
```python
# Agent can use memory tool
memory.add_task("Implement feature X")
memory.update_task("task_1", status="in_progress")
memory.set_context("current_file", "main.py")

# Automatically injected into system prompt
```

**Static Memory** (persistent):
```markdown
# ~/.xagent/memory.md
## 2024-01-15 10:30
User prefers Python 3.12
```

### Output Display

**Collapsible output** for command results:
```
▶ [1] $ pytest tests/  ✗(1)
  Running tests...
  test_foo.py::test_1 PASSED
  ... (5 more lines)

Press 1 to expand | o toggle all | Enter continue
```

**Diff display** for file edits:
```
- 2 │     print('hello')
+ 2 │     print('hello world')
```

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `XAGENT_API_KEY` | API key (required) | - |
| `XAGENT_BASE_URL` | Custom API endpoint | - |
| `XAGENT_MODEL_TYPE` | `openai` / `anthropic` / `litellm` | `openai` |
| `XAGENT_MODEL` | Model name | `gpt-4o` |

### Config File (`~/.xagent/config.yaml`)

```yaml
api_key: "sk-..."
model_type: "openai"
model: "gpt-4o"
max_tokens: 4096
temperature: 0.7
cache_enabled: true
cache_ttl: 86400
dangerous_commands:
  - rm
  - sudo
  - chmod
```

## Extending Xagent

### Adding a New Tool

1. Create tool file:
```python
# tools/my_tool.py
from tools.base import BaseTool

class MyTool(BaseTool):
    name = "my_tool"
    description = "..."
    parameters = {...}

    def run(self, **kwargs) -> str:
        return "result"
```

2. Register in `tools/registry.py`:
```python
from tools.my_tool import MyTool

def _register_builtin_tools(self):
    self.register(MyTool())
```

### Adding a New LLM Provider

1. Create client:
```python
# llm/my_provider.py
from llm.base import BaseLLM, LLMResponse

class MyProviderClient(BaseLLM):
    def chat(self, messages, tools=None) -> LLMResponse:
        ...

    def chat_stream(self, messages, tools=None):
        ...

    def validate_connection(self) -> tuple[bool, str]:
        ...
```

2. Update factory in `llm/__init__.py`:
```python
def get_llm_client(config) -> BaseLLM:
    if config.model_type == "my_provider":
        from llm.my_provider import MyProviderClient
        return MyProviderClient(config)
```

### Creating Plugins

Users can add tools in `~/.xagent/plugins/`:

```python
# ~/.xagent/plugins/web_search.py
from tools.base import BaseTool

class WebSearchTool(BaseTool):
    name = "web_search"
    description = "Search the web"
    parameters = {
        "type": "object",
        "properties": {
            "query": {"type": "string"},
        },
        "required": ["query"],
    }

    def run(self, **kwargs) -> str:
        query = kwargs.get("query")
        # Implement search...
        return "results"
```

### Creating Skills

Skills in `~/.xagent/skills/`:

```python
# ~/.xagent/skills/summarize.py
from core.skills import Skill

skill = Skill(
    name="summarize",
    description="Summarize the conversation",
    handler=lambda: "SKILL:summarize",
)
```

## CLI Commands

| Command | Description |
|---------|-------------|
| `/help` | Show help |
| `/clear` | Clear conversation |
| `/exit` | Exit xagent |
| `/memory` | View/manage static memory |
| `/history` | Show conversation history |
| `/save [name]` | Save session |
| `/load <name>` | Load session |
| `/sessions` | List saved sessions |
| `/cache` | View cache stats |
| `/cache clear` | Clear cache |
| `/config` | Show config |
| `/tools` | List tools |
| `/skills` | List skills |
| `/permissions` | Manage permissions |
| `/permissions pause` | Pause auto-approve |
| `/permissions revoke` | Revoke all auto-approve |

## File Locations

```
~/.xagent/
├── config.yaml          # Configuration
├── memory.md            # Static memory
├── cache/               # Request cache (diskcache)
├── sessions/            # Saved sessions (JSON)
├── plugins/             # User plugins
├── skills/              # User skills
└── logs/
    └── xagent.log       # Debug logs
```

## Testing

```bash
# Install
pip install -e .

# Test imports
python -c "from cli import main; print('OK')"

# Test CLI
xagent --help

# Interactive mode (requires API key)
export XAGENT_API_KEY="your-key"
xagent
```

## Debugging

Enable debug logging:
```python
from utils import setup_logger
logger = setup_logger("DEBUG")
```

Logs: `~/.xagent/logs/xagent.log`

## Security Considerations

1. **Dangerous commands**: Require explicit permission
2. **Recursive calls**: `xagent` commands blocked inside bash
3. **File operations**: Show diff preview before changes
4. **Secrets**: Don't commit `config.yaml` with API keys
