"""Agent core loop for Xagent."""

import json
from typing import Any

from core.config import Config
from core.session import Session
from core.cache import RequestCache
from core.prompts import SYSTEM_PROMPT, MEMORY_INJECTION_TEMPLATE, DYNAMIC_MEMORY_TEMPLATE
from core.permission import PermissionManager
from llm import get_llm_client, LLMResponse
from tools.registry import ToolRegistry
from memory.dynamic import DynamicMemory
from memory.static import StaticMemory
from utils.terminal import TerminalUI
from utils.output import OutputManager


class Agent:
    """Core agent that handles the conversation loop."""

    def __init__(
        self,
        config: Config,
        session: Session | None = None,
        ui: TerminalUI | None = None,
    ):
        self.config = config
        self.session = session or Session()
        self.ui = ui or TerminalUI()
        self.llm = get_llm_client(config)
        self.cache = RequestCache(config)
        self.dynamic_memory = DynamicMemory()
        self.permission_manager = PermissionManager()
        self.output_manager = OutputManager(self.ui.console)
        self.tools = ToolRegistry(
            config,
            self.dynamic_memory,
            self.permission_manager,
            self.output_manager,
        )
        self.static_memory = StaticMemory()
        self.max_iterations = 10

        # Initialize system prompt with memory
        if not self.session.messages:
            self._init_system_prompt()

    def _init_system_prompt(self) -> None:
        """Initialize system prompt with static memory."""
        prompt = SYSTEM_PROMPT

        # Inject static memory if exists
        memory_content = self.static_memory.read()
        if memory_content and memory_content.strip() != "# Xagent Memory":
            prompt += MEMORY_INJECTION_TEMPLATE.format(memory_content=memory_content)

        self.session.add_message("system", prompt)

    def _execute_tool_call(self, tool_call: dict[str, Any]) -> str:
        """Execute a single tool call and return the result."""
        func = tool_call.get("function", {})
        name = func.get("name", "")
        args_str = func.get("arguments", "{}")

        try:
            args = json.loads(args_str)
        except json.JSONDecodeError:
            return f"Error: Invalid JSON arguments: {args_str}"

        self.ui.print_tool_call(name, args)
        result = self.tools.execute(name, **args)

        return result

    def _process_response(self, response: LLMResponse) -> tuple[bool, str | None]:
        """Process LLM response, execute tools if needed.

        Returns (should_continue, final_answer).
        """
        # Update token count
        if response.usage:
            self.session.total_tokens += response.usage.get("total_tokens", 0)
            self.ui.print_tokens(
                response.usage.get("prompt_tokens", 0),
                response.usage.get("completion_tokens", 0),
                response.usage.get("total_tokens", 0),
            )

        # Handle tool calls
        if response.has_tool_calls:
            # Add assistant message with tool calls
            self.session.add_message(
                "assistant",
                response.content,
                tool_calls=response.tool_calls,
            )

            for tool_call in response.tool_calls:
                result = self._execute_tool_call(tool_call)
                tool_name = tool_call.get("function", {}).get("name", "")

                # Check for final_answer
                if tool_name == "final_answer":
                    self.ui.print_final_answer(result)
                    return False, result

                # Add tool result to session
                self.session.add_message(
                    "tool",
                    result,
                    tool_call_id=tool_call.get("id"),
                    name=tool_name,
                )

            return True, None
        else:
            # No tool calls, add assistant message
            self.session.add_message("assistant", response.content)
            return False, None

    def _get_messages_with_dynamic_memory(self) -> list[dict]:
        """Get messages with dynamic memory injected."""
        messages = self.session.get_messages_for_api()

        # Inject dynamic memory summary if exists
        summary = self.dynamic_memory.summarize()
        if summary != "No active tasks or context.":
            dynamic_content = DYNAMIC_MEMORY_TEMPLATE.format(memory_summary=summary)
            # Insert after system message
            for i, msg in enumerate(messages):
                if msg["role"] == "system":
                    messages[i]["content"] += dynamic_content
                    break

        return messages

    def run(self, user_input: str, stream: bool = True) -> str | None:
        """Run the agent loop for a user input.

        Returns the final answer or None if no explicit final_answer was called.
        """
        self.session.add_message("user", user_input)

        for iteration in range(self.max_iterations):
            messages = self._get_messages_with_dynamic_memory()
            tools = self.tools.to_openai_functions()

            # Try cache first (only for non-streaming)
            if not stream:
                cached = self.cache.get(messages, tools, self.config.model)
                if cached:
                    self.ui.print_info("(cached response)")
                    response = LLMResponse(**cached)
                    should_continue, final = self._process_response(response)
                    if not should_continue:
                        return final
                    continue

            # Call LLM
            if stream:
                response = self._run_stream(messages, tools)
            else:
                response = self.llm.chat(messages, tools)
                # Cache the response
                self.cache.set(messages, tools, self.config.model, {
                    "content": response.content,
                    "tool_calls": response.tool_calls,
                    "finish_reason": response.finish_reason,
                    "usage": response.usage,
                })

            should_continue, final = self._process_response(response)
            if not should_continue:
                return final

        self.ui.print_warning("Max iterations reached")
        return None

    def _run_stream(self, messages: list[dict], tools: list[dict]) -> LLMResponse:
        """Run streaming LLM call."""
        gen = self.llm.chat_stream(messages, tools)
        content_parts = []
        response = None

        # Start streaming output
        self.ui.console.print("[bold blue]Agent:[/bold blue] ", end="")

        for chunk in gen:
            self.ui.console.print(chunk, end="", highlight=False)
            content_parts.append(chunk)

        self.ui.console.print()  # Newline after streaming

        # Get final response from generator
        try:
            gen.send(None)
        except StopIteration as e:
            response = e.value

        if response is None:
            response = LLMResponse(content="".join(content_parts))

        return response

    def run_single(self, user_input: str) -> LLMResponse:
        """Run a single LLM call without the agent loop."""
        self.session.add_message("user", user_input)
        messages = self.session.get_messages_for_api()
        response = self.llm.chat(messages, tools=None)
        self.session.add_message("assistant", response.content)
        return response

    def refresh_memory(self) -> None:
        """Refresh static memory in system prompt."""
        # Find and update system message
        for msg in self.session.messages:
            if msg.role == "system":
                prompt = SYSTEM_PROMPT
                memory_content = self.static_memory.read()
                if memory_content and memory_content.strip() != "# Xagent Memory":
                    prompt += MEMORY_INJECTION_TEMPLATE.format(memory_content=memory_content)
                msg.content = prompt
                break
