"""Agent core loop for Xagent."""

import json
import time
from typing import Any

from core.config import Config
from core.session import Session
from core.cache import RequestCache
from core.prompts import SYSTEM_PROMPT, MEMORY_INJECTION_TEMPLATE, DYNAMIC_MEMORY_TEMPLATE, MEMORY_CONSOLIDATION_PROMPT
from core.permission import PermissionManager
from llm import get_llm_client, LLMResponse
from tools.registry import ToolRegistry
from memory.dynamic import DynamicMemory, ConsolidationTrigger, MemoryEntry
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
        self.max_iterations = config.max_iterations

        # Interrupt handling
        self._interrupted = False
        self._running = False

        # Initialize system prompt with memory
        if not self.session.messages:
            self._init_system_prompt()

    def interrupt(self) -> None:
        """Interrupt the current operation."""
        self._interrupted = True
        # Try to interrupt bash tool if running
        bash_tool = self.tools.get("bash")
        if bash_tool and hasattr(bash_tool, "interrupt"):
            bash_tool.interrupt()

    def is_running(self) -> bool:
        """Check if the agent is currently running."""
        return self._running

    def was_interrupted(self) -> bool:
        """Check if last operation was interrupted."""
        return self._interrupted

    def clear_interrupt(self) -> None:
        """Clear the interrupted flag."""
        self._interrupted = False

    def _init_system_prompt(self) -> None:
        """Initialize system prompt with static memory."""
        prompt = SYSTEM_PROMPT

        # Inject static memory if exists
        memory_content = self.static_memory.read()
        if memory_content and memory_content.strip() != "# Xagent Memory":
            prompt += MEMORY_INJECTION_TEMPLATE.format(memory_content=memory_content)

        self.session.add_message("system", prompt)

    def _show_plan_progress(self) -> None:
        """Show current plan progress if exists."""
        tasks = self.dynamic_memory.list_tasks()
        if not tasks:
            return

        self.ui.console.print()
        self.ui.console.print("[dim]─── Plan Progress ───[/dim]")
        for t in tasks:
            if t.status == "completed":
                self.ui.console.print(f"[green]  [✓] {t.description}[/green]")
            elif t.status == "in_progress":
                self.ui.console.print(f"[cyan]  [→] {t.description}[/cyan]")
            else:
                self.ui.console.print(f"[dim]  [ ] {t.description}[/dim]")
        total = len(tasks)
        completed = len([t for t in tasks if t.status == "completed"])
        self.ui.console.print(f"[dim]  ({completed}/{total} completed)[/dim]")
        self.ui.console.print()

    def _execute_tool_call(self, tool_call: dict[str, Any]) -> str:
        """Execute a single tool call and return the result."""
        func = tool_call.get("function", {})
        name = func.get("name", "")
        args_str = func.get("arguments", "{}")

        try:
            args = json.loads(args_str)
        except json.JSONDecodeError:
            return f"Error: Invalid JSON arguments: {args_str}"

        # Check for interrupt
        if self._interrupted:
            return "Operation interrupted by user"

        self.ui.print_tool_start(name, args)
        start_time = time.time()

        try:
            result = self.tools.execute(name, **args)
            elapsed = time.time() - start_time
            success = not result.startswith("Error:")
            self.ui.print_tool_end(name, success=success, elapsed=elapsed)

            # Show progress after completing a plan task
            if name == "plan" and args.get("action") in ("complete", "create"):
                self._show_plan_progress()
                # Trigger: task completed
                if args.get("action") == "complete":
                    self._maybe_consolidate_memory(ConsolidationTrigger.TASK_COMPLETED)

            # Trigger: ask_human response received
            if name == "ask_human":
                self.dynamic_memory.add_interaction(f"User response: {result}")
                self._maybe_consolidate_memory(ConsolidationTrigger.ASK_HUMAN_RESPONSE)

            return result

        except Exception as e:
            elapsed = time.time() - start_time
            self.ui.print_tool_end(name, success=False, message=str(e), elapsed=elapsed)
            return f"Error: {e}"

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
                thinking=response.thinking,
                thinking_signature=response.thinking_signature,
                tool_calls=response.tool_calls,
            )

            final_answer_result = None

            for tool_call in response.tool_calls:
                tool_name = tool_call.get("function", {}).get("name", "")
                tool_call_id = tool_call.get("id")

                # Check for interrupt before executing
                if self._interrupted:
                    # Add empty tool result to keep message history valid
                    self.session.add_message(
                        "tool",
                        "[interrupted by user]",
                        tool_call_id=tool_call_id,
                        name=tool_name,
                    )
                    continue

                result = self._execute_tool_call(tool_call)

                # Always add tool result to session first
                self.session.add_message(
                    "tool",
                    result,
                    tool_call_id=tool_call_id,
                    name=tool_name,
                )

                # Check for final_answer after adding result
                if tool_name == "final_answer":
                    final_answer_result = result

            # If interrupted, stop the loop
            if self._interrupted:
                return False, None

            # Handle final_answer after all tool results are added
            if final_answer_result is not None:
                # Trigger: before final answer
                self._maybe_consolidate_memory(ConsolidationTrigger.BEFORE_FINAL_ANSWER)
                self._persist_consolidated_to_static()
                self.ui.print_final_answer(final_answer_result)
                return False, final_answer_result

            return True, None
        else:
            # No tool calls, add assistant message
            self.session.add_message("assistant", response.content, thinking=response.thinking, thinking_signature=response.thinking_signature)
            return False, None

    def _maybe_consolidate_memory(self, trigger: ConsolidationTrigger) -> None:
        """Conditionally trigger memory consolidation based on event."""
        if not self.config.memory_consolidation_enabled:
            return

        # Layer 2: Token threshold check (always triggers if exceeded)
        if trigger == ConsolidationTrigger.TOKEN_THRESHOLD:
            self._do_consolidate(trigger)
            return

        # Layer 1: Event-based - use LLM to judge if worth saving
        recent_context = self.dynamic_memory.get_recent_context()
        if not recent_context:
            return

        result = self._quick_memory_check(trigger, recent_context)
        if result:
            entry = MemoryEntry(
                type=result.get("type", "project"),
                content=result.get("content", ""),
                trigger=trigger.value,
            )
            self.dynamic_memory.add_consolidated(entry)

    def _quick_memory_check(self, trigger: ConsolidationTrigger, context: str) -> dict | None:
        """Use LLM to quickly judge if recent context is worth remembering."""
        prompt = MEMORY_CONSOLIDATION_PROMPT.format(
            recent_context=context,
            trigger_event=trigger.value,
        )

        try:
            response = self.llm.chat(
                [{"role": "user", "content": prompt}],
                tools=None,
            )
            result = json.loads(response.content)
            if result.get("save"):
                return result
        except (json.JSONDecodeError, Exception):
            pass
        return None

    def _do_consolidate(self, trigger: ConsolidationTrigger) -> None:
        """Force consolidation when token threshold exceeded."""
        summary = self.dynamic_memory.summarize()
        if summary and summary != "No active tasks or context.":
            entry = MemoryEntry(
                type="project",
                content=f"Session state at token threshold:\n{summary}",
                trigger=trigger.value,
            )
            self.dynamic_memory.add_consolidated(entry)

    def _persist_consolidated_to_static(self) -> None:
        """Persist consolidated memories to static storage at session end."""
        entries = self.dynamic_memory.get_consolidated()
        if not entries:
            return

        for entry in entries:
            content = f"[{entry.type}] {entry.content}"
            self.static_memory.append(content)

    def _check_token_threshold(self) -> None:
        """Check if token usage exceeds threshold and trigger consolidation."""
        if not self.config.memory_consolidation_enabled:
            return

        # Estimate based on session tokens
        threshold = self.config.max_tokens * self.config.memory_token_threshold
        if self.session.total_tokens > threshold:
            self._maybe_consolidate_memory(ConsolidationTrigger.TOKEN_THRESHOLD)

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
        was_interrupted = self._interrupted
        self._interrupted = False
        self._running = True

        try:
            self.session.add_message("user", user_input)
            # Track user input for memory consolidation
            self.dynamic_memory.add_interaction(f"User: {user_input}")

            for iteration in range(self.max_iterations):
                # Check for interrupt
                if self._interrupted:
                    self.ui.print_interrupted()
                    return None

                # Check token threshold for memory consolidation
                self._check_token_threshold()

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
                    # Show thinking spinner for non-streaming calls
                    with self.ui.spinner("Thinking..."):
                        response = self.llm.chat(messages, tools)
                    # Cache the response
                    self.cache.set(messages, tools, self.config.model, {
                        "content": response.content,
                        "thinking": response.thinking,
                        "thinking_signature": response.thinking_signature,
                        "tool_calls": response.tool_calls,
                        "finish_reason": response.finish_reason,
                        "usage": response.usage,
                    })

                # Check for interrupt after LLM call
                if self._interrupted:
                    self.ui.print_interrupted()
                    return None

                should_continue, final = self._process_response(response)
                if not should_continue:
                    return final

            self.ui.print_warning("Max iterations reached")
            return None
        finally:
            self._running = False
            # Don't reset _interrupted here - let cli.py check it

    def _run_stream(self, messages: list[dict], tools: list[dict]) -> LLMResponse:
        """Run streaming LLM call."""
        import sys
        import threading

        gen = self.llm.chat_stream(messages, tools)
        content_parts = []
        response = None
        has_printed_prefix = False
        stop_spinner = threading.Event()
        spinner_text = ["Thinking..."]

        # Animated spinner in background thread
        def spinner_thread():
            frames = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
            idx = 0
            while not stop_spinner.is_set():
                sys.stdout.write(f"\r\033[K\033[36m{frames[idx]} {spinner_text[0]}\033[0m")
                sys.stdout.flush()
                idx = (idx + 1) % len(frames)
                stop_spinner.wait(0.1)

        # Start spinner
        spinner = threading.Thread(target=spinner_thread, daemon=True)
        spinner.start()

        try:
            while True:
                try:
                    chunk = next(gen)
                    if chunk:
                        # Check for tool call marker
                        if chunk.startswith("\x00TOOL:") and chunk.endswith("\x00"):
                            tool_name = chunk[6:-1]
                            spinner_text[0] = f"Preparing {tool_name}..."
                            continue

                        if not has_printed_prefix:
                            # Stop spinner and clear line
                            stop_spinner.set()
                            spinner.join(timeout=0.2)
                            sys.stdout.write("\r\033[K")
                            sys.stdout.flush()
                            self.ui.console.print("  ◀ ", end="", style="bold cyan")
                            has_printed_prefix = True

                        self.ui.console.print(chunk, end="", highlight=False)
                        content_parts.append(chunk)
                except StopIteration as e:
                    response = e.value
                    break
        finally:
            stop_spinner.set()
            spinner.join(timeout=0.2)

        # Clear spinner if no content (tool call only)
        if not has_printed_prefix:
            sys.stdout.write("\r\033[K")
            sys.stdout.flush()

        if has_printed_prefix:
            self.ui.console.print()

        if response is None:
            response = LLMResponse(content="".join(content_parts))

        return response

    def run_single(self, user_input: str) -> LLMResponse:
        """Run a single LLM call without the agent loop."""
        self.session.add_message("user", user_input)
        messages = self.session.get_messages_for_api()
        response = self.llm.chat(messages, tools=None)
        self.session.add_message("assistant", response.content, thinking=response.thinking, thinking_signature=response.thinking_signature)
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
