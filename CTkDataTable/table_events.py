"""Public event payloads for CTkDataTable callbacks."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class TableRowEvent:
    """Detailed row event payload with source and view indices."""

    row: dict[str, Any]
    source_index: int
    view_index: int
    column_key: str | None = None
    action_key: str | None = None

