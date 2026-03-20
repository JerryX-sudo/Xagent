"""LLM client implementations."""

from llm.base import BaseLLM, LLMResponse

__all__ = ["BaseLLM", "LLMResponse", "get_llm_client"]


def get_llm_client(config) -> BaseLLM:
    """Factory function to get the appropriate LLM client."""
    if config.model_type == "anthropic":
        from llm.anthropic_client import AnthropicClient
        return AnthropicClient(config)
    else:  # openai or litellm
        from llm.openai_client import OpenAIClient
        return OpenAIClient(config)
