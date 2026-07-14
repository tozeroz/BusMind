from __future__ import annotations

from collections.abc import Callable
import logging
import pickle
from typing import TypeVar

from app.cache.memory_cache_provider import MemoryCacheProvider


try:
    from redis import Redis
    from redis.exceptions import RedisError
except ImportError:  # pragma: no cover - exercised in environments without redis installed.
    Redis = None  # type: ignore[assignment]

    class RedisError(Exception):
        pass


T = TypeVar("T")
logger = logging.getLogger(__name__)


class RedisCacheProvider:
    def __init__(
        self,
        redis_url: str,
        key_prefix: str = "busmind",
        socket_timeout_seconds: float = 2.0,
        fallback: MemoryCacheProvider | None = None,
    ) -> None:
        if Redis is None:
            raise RuntimeError("redis package is not installed")
        self._client = Redis.from_url(
            redis_url,
            socket_timeout=socket_timeout_seconds,
            socket_connect_timeout=socket_timeout_seconds,
            retry_on_timeout=True,
        )
        self._key_prefix = key_prefix.strip().strip(":")
        self._fallback = fallback or MemoryCacheProvider()
        self._warned_unavailable = False
        self._client.ping()

    def get(self, key: str) -> object | None:
        try:
            cached = self._client.get(self._full_key(key))
            if cached is None:
                return self._fallback.get(key)
            return pickle.loads(cached)
        except (RedisError, OSError) as exc:
            self._warn_once("Redis get failed; falling back to memory cache", exc)
            return self._fallback.get(key)
        except (pickle.PickleError, EOFError, AttributeError, ImportError, IndexError) as exc:
            logger.warning("Redis cache payload is invalid for key %s: %s", key, exc)
            self.delete(key)
            return self._fallback.get(key)

    def set(self, key: str, value: object, ttl_seconds: int | float | None = None) -> None:
        self._fallback.set(key, value, ttl_seconds)
        try:
            payload = pickle.dumps(value, protocol=pickle.HIGHEST_PROTOCOL)
            if ttl_seconds is None:
                self._client.set(self._full_key(key), payload)
            else:
                self._client.set(self._full_key(key), payload, ex=max(1, int(ttl_seconds)))
        except (RedisError, OSError, pickle.PickleError) as exc:
            self._warn_once("Redis set failed; value kept in memory cache only", exc)

    def delete(self, key: str) -> None:
        self._fallback.delete(key)
        try:
            self._client.delete(self._full_key(key))
        except (RedisError, OSError) as exc:
            self._warn_once("Redis delete failed; memory cache entry was removed", exc)

    def delete_prefix(self, prefix: str) -> None:
        self._fallback.delete_prefix(prefix)
        try:
            full_prefix = self._full_key(prefix)
            keys = list(self._client.scan_iter(match=f"{full_prefix}*", count=500))
            if keys:
                self._client.delete(*keys)
        except (RedisError, OSError) as exc:
            self._warn_once("Redis delete_prefix failed; memory cache entries were removed", exc)

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

    def ping(self) -> bool:
        try:
            return bool(self._client.ping())
        except (RedisError, OSError):
            return False

    def provider_name(self) -> str:
        return "redis" if self.ping() else "redis_unavailable"

    def _full_key(self, key: str) -> str:
        return f"{self._key_prefix}:{key}" if self._key_prefix else key

    def _warn_once(self, message: str, exc: BaseException) -> None:
        if self._warned_unavailable:
            return
        self._warned_unavailable = True
        logger.warning("%s: %s", message, exc)
