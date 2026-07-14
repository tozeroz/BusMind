from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - production installs python-dotenv via pyproject.
    load_dotenv = None


_ROOT_ENV_PATH = Path(__file__).resolve().parents[3] / ".env"
if load_dotenv is not None:
    load_dotenv(_ROOT_ENV_PATH, override=False)


@dataclass(frozen=True, slots=True)
class CacheSettings:
    cache_backend: str
    redis_url: str | None
    redis_key_prefix: str
    redis_socket_timeout_seconds: float


def get_cache_settings() -> CacheSettings:
    return CacheSettings(
        cache_backend=_clean_backend(os.getenv("CACHE_BACKEND", "auto")),
        redis_url=_optional_text(os.getenv("REDIS_URL")),
        redis_key_prefix=os.getenv("REDIS_KEY_PREFIX", "busmind").strip().strip(":"),
        redis_socket_timeout_seconds=_positive_float(
            os.getenv("REDIS_SOCKET_TIMEOUT_SECONDS"),
            default=2.0,
        ),
    )


def _clean_backend(value: str | None) -> str:
    backend = (value or "auto").strip().lower()
    if backend in {"auto", "redis", "memory"}:
        return backend
    return "auto"


def _optional_text(value: str | None) -> str | None:
    text = (value or "").strip()
    return text or None


def _positive_float(value: str | None, default: float) -> float:
    try:
        parsed = float(value) if value is not None else default
    except ValueError:
        return default
    return parsed if parsed > 0 else default
