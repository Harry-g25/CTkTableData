"""Shared internal helpers for CTkDataTable."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from datetime import date, datetime
from typing import Any


def parse_datetime(value: Any) -> datetime | None:
    """Parse date-like values used by table sorting and display formatting."""

    if isinstance(value, datetime):
        return value
    if isinstance(value, date):
        return datetime.combine(value, datetime.min.time())
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value)
        except ValueError:
            return None
    return None


def normalize_row(row: Any) -> dict[str, Any]:
    """Convert common query row objects into a plain dictionary."""

    if isinstance(row, Mapping):
        return dict(row)

    mapping = getattr(row, "_mapping", None)
    if mapping is not None:
        return dict(mapping)

    keys = getattr(row, "keys", None)
    if callable(keys):
        return {key: row[key] for key in keys()}

    raise TypeError(
        "Rows must be mappings, sqlite3.Row objects, SQLAlchemy mapping rows, "
        "or PostgreSQL rows returned as dictionaries."
    )


def normalize_rows(rows: Iterable[Any]) -> list[dict[str, Any]]:
    """Convert an iterable of row-like objects into plain dictionaries."""

    return [normalize_row(row) for row in rows]


def rows_from_cursor(cursor: Any) -> list[dict[str, Any]]:
    """Convert a DB-API cursor result into dictionaries using cursor.description."""

    if cursor.description is None:
        raise ValueError("Cursor has no result columns. Execute a SELECT query before converting rows.")

    column_names = [column[0] for column in cursor.description]
    return [dict(zip(column_names, row, strict=False)) for row in cursor.fetchall()]
