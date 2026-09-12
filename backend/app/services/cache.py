from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable
from functools import wraps
from typing import Any

logger = logging.getLogger(__name__)


class AsyncTTLCache:
    def __init__(self, ttl_seconds: int = 300, max_items: int = 1000) -> None:
        self.ttl_seconds = ttl_seconds
        self.max_items = max_items
        self.store: dict[str, tuple[Any, float]] = {}
        self.lock = asyncio.Lock()

    async def get(self, key: str) -> Any | None:
        async with self.lock:
            item = self.store.get(key)
            if item is None:
                return None
            value, expires = item
            if expires < asyncio.get_event_loop().time():
                self.store.pop(key, None)
                return None
            return value

    async def set(self, key: str, value: Any) -> None:
        async with self.lock:
            if len(self.store) >= self.max_items:
                self.store.pop(next(iter(self.store)), None)
            self.store[key] = (value, asyncio.get_event_loop().time() + self.ttl_seconds)

    async def delete(self, key: str) -> None:
        async with self.lock:
            self.store.pop(key, None)

    async def clear(self) -> None:
        async with self.lock:
            self.store.clear()

    def cached(self, key_fn: Callable[..., str]) -> Callable[..., Any]:
        def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
            @wraps(func)
            async def wrapper(*args: Any, **kwargs: Any) -> Any:
                key = key_fn(*args, **kwargs)
                value = await self.get(key)
                if value is not None:
                    return value
                result = await func(*args, **kwargs)
                await self.set(key, result)
                return result

            return wrapper

        return decorator


document_cache = AsyncTTLCache(ttl_seconds=300, max_items=500)
