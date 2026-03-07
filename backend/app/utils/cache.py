"""Redis cache utility with in-memory fallback for optimization hooks."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from time import time
from typing import Any


@dataclass
class _MemoryCacheEntry:
    value: str
    expires_at: float


class CacheClient:
    def __init__(self) -> None:
        self._memory_store: dict[str, _MemoryCacheEntry] = {}
        self._redis = None
        redis_url = os.getenv("REDIS_URL")
        if redis_url:
            try:
                import redis as redis_client  # type: ignore[import-not-found]

                self._redis = redis_client.Redis.from_url(redis_url, decode_responses=True)
            except (ImportError, Exception):
                self._redis = None

    def get(self, key: str) -> Any | None:
        if self._redis:
            raw = self._redis.get(key)
            return json.loads(raw) if raw else None

        entry = self._memory_store.get(key)
        if not entry or entry.expires_at < time():
            self._memory_store.pop(key, None)
            return None
        return json.loads(entry.value)

    def set(self, key: str, value: Any, ttl_seconds: int = 60) -> None:
        raw = json.dumps(value, default=str)
        if self._redis:
            self._redis.setex(key, ttl_seconds, raw)
            return
        self._memory_store[key] = _MemoryCacheEntry(value=raw, expires_at=time() + ttl_seconds)

    def delete(self, key: str) -> None:
        if self._redis:
            self._redis.delete(key)
        self._memory_store.pop(key, None)
