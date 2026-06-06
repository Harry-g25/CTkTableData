from __future__ import annotations

import unittest
from collections.abc import Mapping
from datetime import date, datetime
from typing import Any

from CTkDataTable._utils import normalize_row, normalize_rows, parse_datetime, rows_from_cursor


class ParseDatetimeTests(unittest.TestCase):
    def test_parse_datetime_accepts_datetime(self) -> None:
        value = datetime(2026, 6, 3, 12, 30)

        self.assertEqual(parse_datetime(value), value)

    def test_parse_datetime_accepts_date(self) -> None:
        parsed = parse_datetime(date(2026, 6, 3))

        self.assertEqual(parsed, datetime(2026, 6, 3))

    def test_parse_datetime_accepts_iso_string(self) -> None:
        parsed = parse_datetime("2026-06-03T12:30:00")

        self.assertEqual(parsed, datetime(2026, 6, 3, 12, 30))

    def test_parse_datetime_rejects_other_values(self) -> None:
        self.assertIsNone(parse_datetime("not a date"))
        self.assertIsNone(parse_datetime(object()))


class NormalizeRowTests(unittest.TestCase):
    def test_normalize_row_accepts_mapping(self) -> None:
        row = {"id": 1, "name": "Alice"}

        self.assertEqual(normalize_row(row), {"id": 1, "name": "Alice"})

    def test_normalize_row_accepts_sqlalchemy_style_mapping(self) -> None:
        row = _SqlAlchemyStyleRow({"id": 1, "name": "Alice"})

        self.assertEqual(normalize_row(row), {"id": 1, "name": "Alice"})

    def test_normalize_row_accepts_keys_row(self) -> None:
        row = _KeysRow({"id": 1, "name": "Alice"})

        self.assertEqual(normalize_row(row), {"id": 1, "name": "Alice"})

    def test_normalize_rows_accepts_iterables(self) -> None:
        rows = ({"id": index} for index in range(2))

        self.assertEqual(normalize_rows(rows), [{"id": 0}, {"id": 1}])

    def test_normalize_row_rejects_plain_tuples(self) -> None:
        with self.assertRaisesRegex(TypeError, "Rows must be mappings"):
            normalize_row((1, "Alice"))


class RowsFromCursorTests(unittest.TestCase):
    def test_rows_from_cursor_uses_cursor_description(self) -> None:
        cursor = _Cursor(
            description=(("id", None), ("name", None)),
            rows=[(1, "Alice"), (2, "Bob")],
        )

        self.assertEqual(rows_from_cursor(cursor), [{"id": 1, "name": "Alice"}, {"id": 2, "name": "Bob"}])

    def test_rows_from_cursor_requires_result_columns(self) -> None:
        cursor = _Cursor(description=None, rows=[])

        with self.assertRaisesRegex(ValueError, "Cursor has no result columns"):
            rows_from_cursor(cursor)


class _SqlAlchemyStyleRow:
    def __init__(self, values: Mapping[str, Any]) -> None:
        self._mapping = values


class _KeysRow:
    def __init__(self, values: Mapping[str, Any]) -> None:
        self._values = values

    def keys(self) -> list[str]:
        return list(self._values.keys())

    def __getitem__(self, key: str) -> Any:
        return self._values[key]


class _Cursor:
    def __init__(self, *, description: Any, rows: list[tuple[Any, ...]]) -> None:
        self.description = description
        self._rows = rows

    def fetchall(self) -> list[tuple[Any, ...]]:
        return self._rows


if __name__ == "__main__":
    unittest.main()
