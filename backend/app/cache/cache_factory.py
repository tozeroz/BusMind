from __future__ import annotations

import logging

from app.cache.cache_provider import CacheProvider
from app.cache.cache_settings import CacheSettings, get_cache_settings
from app.cache.memory_cache_provider import MemoryCacheProvider
from app.cache.redis_cache_provider import RedisCacheProvider


logger = logging.getLogger(__name__)


def create_cache_provider(settings: CacheSettings | None = None) -> CacheProvider:
    cache_settings = settings or get_cache_settings()
    memory_provider = MemoryCacheProvider()

    if cache_settings.cache_backend == "memory":
        logger.info("Using memory cache provider")
        return memory_provider

    if not cache_settings.redis_url:
        logger.info("REDIS_URL is not configured; using memory cache provider")
        return memory_provider

    try:
        redis_provider = RedisCacheProvider(
            redis_url=cache_settings.redis_url,
            key_prefix=cache_settings.redis_key_prefix,
            socket_timeout_seconds=cache_settings.redis_socket_timeout_seconds,
            fallback=memory_provider,
        )
    except Exception as exc:
        logger.warning("Redis cache provider is unavailable; using memory cache provider: %s", exc)
        return memory_provider

    logger.info("Using Redis cache provider")
    return redis_provider


def get_cache_provider_name(provider: CacheProvider) -> str:
    name_getter = getattr(provider, "provider_name", None)
    if callable(name_getter):
        return str(name_getter())
    if isinstance(provider, MemoryCacheProvider):
        return "memory"
    return provider.__class__.__name__
