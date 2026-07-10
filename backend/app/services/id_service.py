"""Helpers for tables whose production primary keys are not AUTO_INCREMENT."""

from __future__ import annotations

from sqlalchemy import func
from sqlalchemy.orm import Session


def next_numeric_id(db: Session, column) -> int:
    """Return the next numeric identifier for low-volume administrative inserts.

    Imported LTA data keeps its pre-generated IDs. For manual create APIs the caller
    may provide an ID; when omitted this helper chooses max(id) + 1. These endpoints
    are administrative and low-volume. High-concurrency ID allocation should use a
    dedicated sequence service or require an explicit ID.
    """

    current = db.query(func.max(column)).scalar()
    return int(current or 0) + 1


def station_id_from_code(code: str | None) -> int | None:
    """Use the same numeric BusStopCode convention as the processed-data pipeline."""

    if not code:
        return None
    normalized = str(code).strip()
    if normalized.endswith(".0"):
        normalized = normalized[:-2]
    if normalized.isdigit():
        return int(normalized)
    return None
