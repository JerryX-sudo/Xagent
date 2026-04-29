"""Anthropic native LLM client."""

import json
from typing import Any, Generator

from anthropic import Anthropic, APIError, APIConnectionError, AuthenticationError

from llm.base import BaseLLM, LLMResponse


class AnthropicClient(BaseLLM):
    """Anthropic native client."""

    def __init__(self, config):
        super().__init__(config)
        self.client = Anthropic(api_key=config.api_key)
        # Default to Claude model if not specified
        if not config.model or config.model.startswith("gpt"):
            self.model = "claude-sonnet-4-20250514"
        else:
            self.model = config.model

    def _convert_tools_to_anthropic(
        self, tools: list[dict[str, Any]] | None
    ) -> list[dict[str, Any]] | None:
        """Convert OpenAI tool format to Anthropic format."""
        if not tools:
            return None

        anthropic_tools = []
        for tool in tools:
            if tool.get("type") == "function":
                func = tool["function"]
                anthropic_tools.append({
                    "name": func["name"],
                    "description": func.get("description", ""),
                    "input_schema": func.get("parameters", {"type": "object", "properties": {}}),
                })
        return anthropic_tools

    def _convert_messages_to_anthropic(
        self, messages: list[dict[str, Any]]
    ) -> tuple[str | None, list[dict[str, Any]]]:
        """Convert OpenAI message format to Anthropic format."""
        system_prompt = None
        anthropic_messages = []

        for msg in messages:
            role = msg["role"]

            if role == "system":
                system_prompt = msg["content"]
            elif role == "user":
                anthropic_messages.append({"role": "user", "content": msg["content"]})
            elif role == "assistant":
                content: list[dict[str, Any]] = []
                if msg.get("thinking"):
                    content.append({"type": "thinking", "thinking": msg["thinking"]})
                if msg.get("content"):
                    content.append({"type": "text", "text": msg["content"]})
                if msg.get("tool_calls"):
                    for tc in msg["tool_calls"]:
                        content.append({
                            "type": "tool_use",
                            "id": tc["id"],
                            "name": tc["function"]["name"],
                            "input": json.loads(tc["function"]["arguments"]),
                        })
                anthropic_messages.append({"role": "assistant", "content": content or msg["content"]})
            elif role == "tool":
                anthropic_messages.append({
                    "role": "user",
                    "content": [{
                        "type": "tool_result",
                        "tool_use_id": msg["tool_call_id"],
                        "content": msg["content"],
                    }],
                })

        return system_prompt, anthropic_messages

    def chat(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
    ) -> LLMResponse:
        """Send a chat request and return the response."""
        system_prompt, anthropic_messages = self._convert_messages_to_anthropic(messages)
        anthropic_tools = self._convert_tools_to_anthropic(tools)

        kwargs: dict[str, Any] = {
            "model": self.model,
            "messages": anthropic_messages,
            "max_tokens": self.config.max_tokens,
        }

        if system_prompt:
            kwargs["system"] = system_prompt
        if anthropic_tools:
            kwargs["tools"] = anthropic_tools

        try:
            response = self.client.messages.create(**kwargs)
        except (APIError, APIConnectionError) as e:
            raise RuntimeError(f"API error: {e}") from e

        content_parts = []
        thinking_parts = []
        tool_calls = []

        for block in response.content:
            if block.type == "text":
                content_parts.append(block.text)
            elif block.type == "thinking":
                thinking_parts.append(block.thinking)
            elif block.type == "tool_use":
                tool_calls.append({
                    "id": block.id,
                    "type": "function",
                    "function": {
                        "name": block.name,
                        "arguments": json.dumps(block.input),
                    },
                })

        return LLMResponse(
            content="".join(content_parts),
            thinking="".join(thinking_parts) if thinking_parts else None,
            tool_calls=tool_calls if tool_calls else None,
            finish_reason="tool_calls" if tool_calls else response.stop_reason or "stop",
            usage={
                "prompt_tokens": response.usage.input_tokens,
                "completion_tokens": response.usage.output_tokens,
                "total_tokens": response.usage.input_tokens + response.usage.output_tokens,
            },
        )

    def chat_stream(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
    ) -> Generator[str, None, LLMResponse]:
        """Stream a chat response, yielding content chunks."""
        system_prompt, anthropic_messages = self._convert_messages_to_anthropic(messages)
        anthropic_tools = self._convert_tools_to_anthropic(tools)

        kwargs: dict[str, Any] = {
            "model": self.model,
            "messages": anthropic_messages,
            "max_tokens": self.config.max_tokens,
        }

        if system_prompt:
            kwargs["system"] = system_prompt
        if anthropic_tools:
            kwargs["tools"] = anthropic_tools

        try:
            stream = self.client.messages.stream(**kwargs)
        except (APIError, APIConnectionError) as e:
            raise RuntimeError(f"API error: {e}") from e

        content_parts: list[str] = []
        thinking_parts: list[str] = []
        tool_calls: list[dict[str, Any]] = []
        current_tool: dict[str, Any] | None = None
        current_thinking: bool = False
        input_json = ""

        with stream as s:
            for event in s:
                if event.type == "content_block_start":
                    if event.content_block.type == "thinking":
                        current_thinking = True
                    elif event.content_block.type == "tool_use":
                        current_thinking = False
                        current_tool = {
                            "id": event.content_block.id,
                            "type": "function",
                            "function": {
                                "name": event.content_block.name,
                                "arguments": "",
                            },
                        }
                        input_json = ""
                        # Announce tool call with special marker
                        yield f"\x00TOOL:{event.content_block.name}\x00"
                    else:
                        current_thinking = False
                elif event.type == "content_block_delta":
                    if hasattr(event.delta, "thinking"):
                        thinking_parts.append(event.delta.thinking)
                    elif hasattr(event.delta, "text"):
                        content_parts.append(event.delta.text)
                        yield event.delta.text
                    elif hasattr(event.delta, "partial_json"):
                        input_json += event.delta.partial_json
                elif event.type == "content_block_stop":
                    if current_tool:
                        current_tool["function"]["arguments"] = input_json
                        tool_calls.append(current_tool)
                        current_tool = None
                    current_thinking = False

            final_message = s.get_final_message()

        return LLMResponse(
            content="".join(content_parts),
            thinking="".join(thinking_parts) if thinking_parts else None,
            tool_calls=tool_calls if tool_calls else None,
            finish_reason="tool_calls" if tool_calls else "stop",
            usage={
                "prompt_tokens": final_message.usage.input_tokens,
                "completion_tokens": final_message.usage.output_tokens,
                "total_tokens": final_message.usage.input_tokens + final_message.usage.output_tokens,
            },
        )

    def validate_connection(self) -> tuple[bool, str]:
        """Validate the API connection."""
        try:
            self.client.messages.create(
                model=self.model,
                max_tokens=10,
                messages=[{"role": "user", "content": "Hi"}],
            )
            return True, "Connection successful"
        except AuthenticationError:
            return False, "Invalid API key"
        except APIConnectionError as e:
            return False, f"Connection failed: {e}"
        except Exception as e:
            return False, f"Unexpected error: {e}"
