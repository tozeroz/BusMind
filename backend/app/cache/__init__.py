from backend.app.cache.cache_provider import CacheProvider
from backend.app.cache.memory_cache_provider import MemoryCacheProvider

memory_cache_provider = MemoryCacheProvider()

__all__ = ["CacheProvider", "MemoryCacheProvider", "memory_cache_provider"]
