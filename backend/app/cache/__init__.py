from app.cache.cache_provider import CacheProvider
from app.cache.cache_factory import create_cache_provider, get_cache_provider_name
from app.cache.memory_cache_provider import MemoryCacheProvider
from app.cache.redis_cache_provider import RedisCacheProvider

cache_provider = create_cache_provider()
memory_cache_provider = cache_provider

__all__ = [
    "CacheProvider",
    "MemoryCacheProvider",
    "RedisCacheProvider",
    "cache_provider",
    "get_cache_provider_name",
    "memory_cache_provider",
]

