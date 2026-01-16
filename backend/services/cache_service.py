"""
Lightweight caching service with optional Redis backend.
Falls back to in-memory cache when Redis is unavailable.
"""
import json
import time
import logging
from typing import Any, Optional

from backend.config import settings

try:
    import redis  # type: ignore
except ImportError:  # pragma: no cover
    redis = None

logger = logging.getLogger(__name__)


class CacheService:
    """Caching helper with TTL support."""

    def __init__(self):
        self.redis_url = getattr(settings, "redis_url", None)
        self.client = None
        if redis and self.redis_url:
            try:
                self.client = redis.from_url(self.redis_url, decode_responses=True)
                self.client.ping()
                logger.info("Redis cache connected")
            except Exception as exc:  # pragma: no cover
                logger.warning(f"Redis unavailable, using in-memory cache: {exc}")
                self.client = None
        self._memory_cache: dict[str, tuple[float, str]] = {}

    def get(self, key: str) -> Optional[Any]:
        """Retrieve cached value if present and not expired."""
        if self.client:
            try:
                data = self.client.get(key)
                if data is None:
                    return None
                return json.loads(data)
            except Exception as exc:  # pragma: no cover
                logger.warning(f"Redis get failed: {exc}")
                return None
        # In-memory fallback
        item = self._memory_cache.get(key)
        if not item:
            return None
        expires_at, payload = item
        if time.time() > expires_at:
            self._memory_cache.pop(key, None)
            return None
        return json.loads(payload)

    def set(self, key: str, value: Any, ttl_seconds: int = 300) -> None:
        """Store value with TTL."""
        serialized = json.dumps(value, default=str)
        if self.client:
            try:
                self.client.setex(key, ttl_seconds, serialized)
                return
            except Exception as exc:  # pragma: no cover
                logger.warning(f"Redis set failed: {exc}")
        expires_at = time.time() + ttl_seconds
        self._memory_cache[key] = (expires_at, serialized)

    def delete(self, key: str) -> None:
        """Delete cached value."""
        if self.client:
            try:
                self.client.delete(key)
            except Exception as exc:  # pragma: no cover
                logger.warning(f"Redis delete failed: {exc}")
        self._memory_cache.pop(key, None)

    def clear_prefix(self, prefix: str) -> None:
        """Clear keys matching prefix (best effort)."""
        if self.client:
            try:  # pragma: no cover
                keys = self.client.keys(f"{prefix}*")
                if keys:
                    self.client.delete(*keys)
            except Exception as exc:
                logger.warning(f"Redis clear_prefix failed: {exc}")
        keys_to_delete = [k for k in self._memory_cache if k.startswith(prefix)]
        for k in keys_to_delete:
            self._memory_cache.pop(k, None)


cache_service = CacheService()
