from __future__ import annotations

from app.cache.memory_cache_provider import MemoryCacheProvider
from app.cache.redis_cache_provider import RedisCacheProvider


class FakeRedisClient:
    def __init__(self) -> None:
        self.items: dict[str, bytes] = {}
        self.expires: dict[str, int] = {}

    def ping(self) -> bool:
        return True

    def get(self, key: str) -> bytes | None:
        return self.items.get(key)

    def set(self, key: str, value: bytes, ex: int | None = None) -> None:
        self.items[key] = value
        if ex is not None:
            self.expires[key] = ex

    def delete(self, *keys: str) -> None:
        for key in keys:
            self.items.pop(key, None)
            self.expires.pop(key, None)

    def scan_iter(self, match: str, count: int = 500):
        prefix = match[:-1] if match.endswith("*") else match
        return [key for key in self.items if key.startswith(prefix)]


class FakeRedis:
    client = FakeRedisClient()

    @classmethod
    def from_url(cls, *_args, **_kwargs):
        return cls.client


def test_redis_cache_provider_round_trips_pickled_values(monkeypatch):
    FakeRedis.client = FakeRedisClient()
    monkeypatch.setattr("app.cache.redis_cache_provider.Redis", FakeRedis)

    provider = RedisCacheProvider("redis://localhost:6379/0", key_prefix="busmind-test")
    provider.set("bus_arrival:83139", {"eta_minutes": 4.0}, ttl_seconds=75)

    assert provider.get("bus_arrival:83139") == {"eta_minutes": 4.0}
    assert FakeRedis.client.expires["busmind-test:bus_arrival:83139"] == 75


def test_redis_cache_provider_deletes_by_prefix(monkeypatch):
    FakeRedis.client = FakeRedisClient()
    monkeypatch.setattr("app.cache.redis_cache_provider.Redis", FakeRedis)
    provider = RedisCacheProvider("redis://localhost:6379/0", key_prefix="busmind-test")
    provider.set("map:stations:v1:all", ["a"])
    provider.set("map:stations:v1:1", ["b"])
    provider.set("map:lines:v1", ["c"])

    provider.delete_prefix("map:stations")

    assert provider.get("map:stations:v1:all") is None
    assert provider.get("map:stations:v1:1") is None
    assert provider.get("map:lines:v1") == ["c"]


def test_redis_cache_provider_falls_back_to_memory(monkeypatch):
    class BrokenRedis(FakeRedis):
        @classmethod
        def from_url(cls, *_args, **_kwargs):
            client = FakeRedisClient()

            def broken_get(_key):
                raise RuntimeError("redis down")

            client.get = broken_get
            return client

    fallback = MemoryCacheProvider()
    fallback.set("recommend:1", {"items": []})
    monkeypatch.setattr("app.cache.redis_cache_provider.Redis", BrokenRedis)
    monkeypatch.setattr("app.cache.redis_cache_provider.RedisError", RuntimeError)

    provider = RedisCacheProvider("redis://localhost:6379/0", fallback=fallback)

    assert provider.get("recommend:1") == {"items": []}


def test_redis_cache_provider_discards_invalid_payload(monkeypatch):
    FakeRedis.client = FakeRedisClient()
    FakeRedis.client.items["busmind-test:bad"] = b"not-pickle"
    monkeypatch.setattr("app.cache.redis_cache_provider.Redis", FakeRedis)
    provider = RedisCacheProvider("redis://localhost:6379/0", key_prefix="busmind-test")

    assert provider.get("bad") is None
    assert FakeRedis.client.items.get("busmind-test:bad") is None
