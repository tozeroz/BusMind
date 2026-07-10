from __future__ import annotations

from collections.abc import Callable
from typing import Protocol, TypeVar


T = TypeVar("T")


class CacheProvider(Protocol):
    def get(self, key: str) -> object | None: ...

    def set(self, key: str, value: object, ttl_seconds: int | float | None = None) -> None: ...

    def delete(self, key: str) -> None: ...

    def get_or_set(
        self,
        key: str,
        loader: Callable[[], T],
        ttl_seconds: int | float | None = None,
    ) -> T: ...
