"""OpenAI-compatible LLM client."""

from typing import Any, Generator

from openai import OpenAI, APIError, APIConnectionError, AuthenticationError

from llm.base import BaseLLM, LLMResponse


def _get_reasoning_content(obj) -> str | None:
    """Extract reasoning_content from an OpenAI SDK object (attribute or model_extra)."""
    rc = getattr(obj, "reasoning_content", None)
    if rc is not None:
        return rc
    model_extra = getattr(obj, "model_extra", None)
    if model_extra:
        return model_extra.get("reasoning_content")
    return None


class OpenAIClient(BaseLLM):
    """OpenAI-compatible client (works with OpenAI, LiteLLM, etc.)."""

    def __init__(self, config):
        super().__init__(config)
        # Ensure base_url has /v1 suffix for OpenAI SDK compatibility
        base_url = config.base_url
        if base_url and not base_url.rstrip('/').endswith('/v1'):
            base_url = base_url.rstrip('/') + '/v1'
        self.client = OpenAI(
            api_key=config.api_key,
            base_url=base_url,
        )

    def chat(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
    ) -> LLMResponse:
        """Send a chat request and return the response."""
        kwargs: dict[str, Any] = {
            "model": self.config.model,
            "messages": messages,
            "max_tokens": self.config.max_tokens,
            "temperature": self.config.temperature,
        }

        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = "auto"

        try:
            response = self.client.chat.completions.create(**kwargs)
        except (APIError, APIConnectionError) as e:
            raise RuntimeError(f"API error: {e}") from e

        message = response.choices[0].message

        tool_calls = None
        if message.tool_calls:
            tool_calls = [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments,
                    },
                }
                for tc in message.tool_calls
            ]

        # Always capture reasoning_content (DeepSeek reasoner requires it back)
        reasoning_content = _get_reasoning_content(message) or _get_reasoning_content(response.choices[0])

        return LLMResponse(
            content=message.content or "",
            thinking=reasoning_content,
            tool_calls=tool_calls,
            finish_reason=response.choices[0].finish_reason or "stop",
            usage={
                "prompt_tokens": response.usage.prompt_tokens if response.usage else 0,
                "completion_tokens": response.usage.completion_tokens if response.usage else 0,
                "total_tokens": response.usage.total_tokens if response.usage else 0,
            },
        )

    def chat_stream(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
    ) -> Generator[str, None, LLMResponse]:
        """Stream a chat response, yielding content chunks."""
        kwargs: dict[str, Any] = {
            "model": self.config.model,
            "messages": messages,
            "max_tokens": self.config.max_tokens,
            "temperature": self.config.temperature,
            "stream": True,
        }

        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = "auto"

        try:
            stream = self.client.chat.completions.create(**kwargs)
        except (APIError, APIConnectionError) as e:
            raise RuntimeError(f"API error: {e}") from e

        content_parts: list[str] = []
        reasoning_parts: list[str] = []
        tool_calls_data: dict[int, dict[str, Any]] = {}
        finish_reason = "stop"
        tool_call_announced: set[int] = set()

        for chunk in stream:
            if not chunk.choices:
                continue

            delta = chunk.choices[0].delta

            # Always capture reasoning_content (DeepSeek reasoner requires it back)
            rc = _get_reasoning_content(delta) or _get_reasoning_content(chunk.choices[0])
            if rc is not None:
                reasoning_parts.append(rc)

            if delta.content:
                content_parts.append(delta.content)
                yield delta.content

            if delta.tool_calls:
                for tc in delta.tool_calls:
                    idx = tc.index
                    if idx not in tool_calls_data:
                        tool_calls_data[idx] = {
                            "id": tc.id or "",
                            "type": "function",
                            "function": {"name": "", "arguments": ""},
                        }
                    if tc.id:
                        tool_calls_data[idx]["id"] = tc.id
                    if tc.function:
                        if tc.function.name:
                            tool_calls_data[idx]["function"]["name"] = tc.function.name
                            # Announce tool call with special marker
                            if idx not in tool_call_announced:
                                tool_call_announced.add(idx)
                                yield f"\x00TOOL:{tc.function.name}\x00"
                        if tc.function.arguments:
                            tool_calls_data[idx]["function"]["arguments"] += tc.function.arguments

            if chunk.choices[0].finish_reason:
                finish_reason = chunk.choices[0].finish_reason

        tool_calls = None
        if tool_calls_data:
            tool_calls = [tool_calls_data[i] for i in sorted(tool_calls_data.keys())]

        return LLMResponse(
            content="".join(content_parts),
            thinking="".join(reasoning_parts) if reasoning_parts else None,
            tool_calls=tool_calls,
            finish_reason=finish_reason,
        )

    def validate_connection(self) -> tuple[bool, str]:
        """Validate the API connection."""
        try:
            # Use chat request instead of models.list()
            # Some proxies don't support the models endpoint
            self.client.chat.completions.create(
                model=self.config.model,
                messages=[{"role": "user", "content": "hi"}],
                max_tokens=1,
            )
            return True, "Connection successful"
        except AuthenticationError:
            return False, "Invalid API key"
        except APIConnectionError as e:
            return False, f"Connection failed: {e}"
        except Exception as e:
            return False, f"Unexpected error: {e}"
