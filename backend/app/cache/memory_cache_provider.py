from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from threading import RLock
from time import monotonic
from typing import TypeVar


T = TypeVar("T")


@dataclass(slots=True)
class _CacheEntry:
    value: object
    expire_at: float | None


class MemoryCacheProvider:
    def __init__(self) -> None:
        self._items: dict[str, _CacheEntry] = {}
        self._lock = RLock()

    def get(self, key: str) -> object | None:
        with self._lock:
            entry = self._items.get(key)
            if entry is None:
                return None
            if entry.expire_at is not None and entry.expire_at <= monotonic():
                self._items.pop(key, None)
                return None
            return entry.value

    def set(self, key: str, value: object, ttl_seconds: int | float | None = None) -> None:
        expire_at = None if ttl_seconds is None else monotonic() + max(float(ttl_seconds), 0.0)
        with self._lock:
            self._items[key] = _CacheEntry(value=value, expire_at=expire_at)

    def delete(self, key: str) -> None:
        with self._lock:
            self._items.pop(key, None)

    def delete_prefix(self, prefix: str) -> None:
        with self._lock:
            keys = [key for key in self._items if key.startswith(prefix)]
            for key in keys:
                self._items.pop(key, None)

    def get_or_set(
        self,
        key: str,
        loader: Callable[[], T],
        ttl_seconds: int | float | None = None,
    ) -> T:
        cached = self.get(key)
        if cached is not None:
            return cached  # type: ignore[return-value]
        value = loader()
        self.set(key, value, ttl_seconds)
        return value

    def clear_expired(self) -> int:
        now = monotonic()
        with self._lock:
            expired = [key for key, entry in self._items.items() if entry.expire_at is not None and entry.expire_at <= now]
            for key in expired:
                self._items.pop(key, None)
            return len(expired)
