"""Request caching for Xagent."""

import hashlib
import json
from typing import Any

from diskcache import Cache

from core.config import Config


class RequestCache:
    """Cache for LLM requests to save tokens."""

    def __init__(self, config: Config):
        self.config = config
        self.cache_dir = Config.get_config_dir() / "cache"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._cache = Cache(str(self.cache_dir))

    def _make_key(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None,
        model: str,
    ) -> str:
        """Generate a cache key from request parameters."""
        key_data = {
            "messages": messages,
            "tools": tools or [],
            "model": model,
        }
        key_str = json.dumps(key_data, sort_keys=True)
        return hashlib.sha256(key_str.encode()).hexdigest()

    def get(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None,
        model: str,
    ) -> dict[str, Any] | None:
        """Get cached response if available."""
        if not self.config.cache_enabled:
            return None

        key = self._make_key(messages, tools, model)
        return self._cache.get(key)

    def set(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None,
        model: str,
        response: dict[str, Any],
    ) -> None:
        """Cache a response."""
        if not self.config.cache_enabled:
            return

        key = self._make_key(messages, tools, model)
        self._cache.set(key, response, expire=self.config.cache_ttl)

    def clear(self) -> int:
        """Clear all cached responses. Returns number of items cleared."""
        count = len(self._cache)
        self._cache.clear()
        return count

    def stats(self) -> dict[str, Any]:
        """Get cache statistics."""
        return {
            "size": len(self._cache),
            "directory": str(self.cache_dir),
            "enabled": self.config.cache_enabled,
            "ttl": self.config.cache_ttl,
        }

    def close(self) -> None:
        """Close the cache."""
        self._cache.close()
