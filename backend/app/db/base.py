"""Shared SQLAlchemy declarative base and database-compatible column types.

The production schema uses MySQL BIGINT primary keys. SQLite only auto-increments an
INTEGER PRIMARY KEY, so BIGINT_COMPAT keeps MySQL as BIGINT while using INTEGER in
SQLite-based local tests.
"""

from sqlalchemy import BigInteger, Integer
from secrets import randbelow
from uuid import uuid4
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Single metadata registry for every BusMind ORM model."""


BIGINT_COMPAT = BigInteger().with_variant(Integer, "sqlite")


def runtime_bigint_id() -> int:
    """Client-side fallback ID used only when an ORM insert omits a non-auto ID."""

    return 1_000_000_000_000 + randbelow(8_000_000_000_000)


def runtime_string_id() -> str:
    return uuid4().hex[:24]
