from __future__ import annotations

import unittest
from datetime import date

from CTkDataTable.table_column import normalize_columns
from CTkDataTable.table_model import TableModel


class TableModelTests(unittest.TestCase):
    def test_filter_searches_visible_non_action_columns_and_prunes_selection(self) -> None:
        model = TableModel(_columns(), _rows())
        model.select_view_index(0)

        changed = model.filter("closed")

        self.assertEqual(model.view_indices, [1])
        self.assertEqual(model.get_selected_source_indices(), [])
        self.assertEqual(changed, {0})

    def test_sort_by_number_places_missing_values_last(self) -> None:
        model = TableModel(_columns(), _rows())

        model.sort_by("amount", ascending=True)

        self.assertEqual([model.row_for_view_index(index)["id"] for index in range(3)], [2, 1, 3])

    def test_sort_by_currency_and_progress_uses_numeric_semantics(self) -> None:
        model = TableModel(
            normalize_columns(
                [
                    {"key": "id", "title": "ID", "width": 80, "type": "number"},
                    {"key": "cost", "title": "Cost", "width": 120, "type": "currency"},
                    {"key": "completion", "title": "Done", "width": 140, "type": "progress"},
                ]
            ),
            [
                {"id": 1, "cost": "1,200", "completion": 20},
                {"id": 2, "cost": 75, "completion": "5"},
                {"id": 3, "cost": None, "completion": None},
            ],
        )

        model.sort_by("cost", ascending=True)
        self.assertEqual([model.row_for_view_index(index)["id"] for index in range(3)], [2, 1, 3])

        model.sort_by("completion", ascending=False)
        self.assertEqual([model.row_for_view_index(index)["id"] for index in range(3)], [1, 2, 3])

    def test_sort_by_percentage_uses_numeric_semantics(self) -> None:
        model = TableModel(
            normalize_columns(
                [
                    {"key": "id", "title": "ID", "width": 80, "type": "number"},
                    {"key": "margin", "title": "Margin", "width": 120, "type": "percentage"},
                ]
            ),
            [
                {"id": 1, "margin": "12.5"},
                {"id": 2, "margin": 4},
                {"id": 3, "margin": None},
            ],
        )

        model.sort_by("margin", ascending=True)

        self.assertEqual([model.row_for_view_index(index)["id"] for index in range(3)], [2, 1, 3])

    def test_descending_numeric_sort_keeps_invalid_values_last(self) -> None:
        model = TableModel(
            normalize_columns(
                [
                    {"key": "id", "title": "ID", "width": 80, "type": "number"},
                    {"key": "amount", "title": "Amount", "width": 120, "type": "number"},
                ]
            ),
            [
                {"id": 1, "amount": "not numeric"},
                {"id": 2, "amount": 75},
                {"id": 3, "amount": 120},
            ],
        )

        model.sort_by("amount", ascending=False)

        self.assertEqual([model.row_for_view_index(index)["id"] for index in range(3)], [3, 2, 1])

    def test_sort_by_date_uses_date_semantics(self) -> None:
        model = TableModel(_columns(), _rows())

        model.sort_by("created", ascending=False)

        self.assertEqual([model.row_for_view_index(index)["id"] for index in range(3)], [3, 2, 1])

    def test_multi_select_and_delete_shift_source_indices(self) -> None:
        model = TableModel(_columns(), _rows())
        model.select_view_index(0, multi_select=True)
        model.select_view_index(2, multi_select=True, control=True)

        model.delete_row(0)

        self.assertEqual(model.get_selected_source_indices(), [1])
        self.assertEqual(
            model.get_selected_rows(),
            [{"id": 3, "name": "Charlie", "status": "Open", "amount": None, "created": date(2026, 6, 3)}],
        )

    def test_shift_select_uses_current_view_order(self) -> None:
        model = TableModel(_columns(), _rows())
        model.sort_by("amount")
        model.select_view_index(0, multi_select=True)
        model.select_view_index(1, multi_select=True, shift=True)

        self.assertEqual(model.get_selected_source_indices(), [1, 0])
        self.assertEqual(model.get_selected_view_indices(), [0, 1])

    def test_delete_row_by_key_removes_first_matching_row(self) -> None:
        model = TableModel(_columns(), _rows())

        self.assertTrue(model.delete_row_by_key("id", 2))
        self.assertFalse(model.delete_row_by_key("id", 999))
        self.assertEqual([row["id"] for row in model.get_data()], [1, 3])

    def test_find_source_index_requires_known_column(self) -> None:
        model = TableModel(_columns(), _rows())

        self.assertEqual(model.find_source_index("name", "Alice"), 0)
        with self.assertRaisesRegex(KeyError, "Unknown column key 'missing'"):
            model.find_source_index("missing", "Alice")

    def test_column_filters_can_be_combined_with_search(self) -> None:
        model = TableModel(_columns(), _rows())

        changed = model.set_column_filter("status", {"type": "equals", "value": "Open"})
        model.search("charlie")

        self.assertEqual(changed, set())
        self.assertEqual(model.view_indices, [2])
        self.assertEqual(
            model.get_visible_rows(),
            [{"id": 3, "name": "Charlie", "status": "Open", "amount": None, "created": date(2026, 6, 3)}],
        )

    def test_number_range_column_filter(self) -> None:
        model = TableModel(_columns(), _rows())

        model.set_column_filter("amount", {"type": "range", "min": 50, "max": 1300})

        self.assertEqual([model.row_for_view_index(index)["id"] for index in range(2)], [1, 2])

    def test_callable_column_filter(self) -> None:
        model = TableModel(_columns(), _rows())

        model.set_column_filter("name", lambda value, _row: str(value).startswith(("A", "C")))

        self.assertEqual([model.row_for_view_index(index)["id"] for index in range(2)], [1, 3])

    def test_column_filter_definitions_are_validated_when_set(self) -> None:
        model = TableModel(_columns(), _rows())

        with self.assertRaisesRegex(ValueError, "invalid min date value"):
            model.set_column_filter("created", {"type": "date_range", "min": "not a date"})

        with self.assertRaisesRegex(TypeError, "non-string iterable 'values'"):
            model.set_column_filter("status", {"type": "in", "values": "Open"})

    def test_set_columns_drops_incompatible_sort_and_filters(self) -> None:
        model = TableModel(_columns(), _rows())
        model.sort_by("amount")
        model.set_column_filter("status", {"type": "equals", "value": "Open"})

        model.set_columns(normalize_columns([{"key": "id", "title": "ID", "width": 80}]))

        self.assertIsNone(model.sort_state)
        self.assertEqual(model.column_filters, {})


def _columns():
    return normalize_columns(
        [
            {"key": "id", "title": "ID", "width": 80, "type": "number"},
            {"key": "name", "title": "Name", "width": 160},
            {"key": "status", "title": "Status", "width": 120, "type": "badge"},
            {"key": "amount", "title": "Amount", "width": 120, "type": "number"},
            {"key": "created", "title": "Created", "width": 120, "type": "date"},
            {"key": "actions", "title": "Actions", "width": 120, "type": "action", "actions": ["view"]},
        ]
    )


def _rows():
    return [
        {"id": 1, "name": "Alice", "status": "Open", "amount": "1,200", "created": date(2026, 6, 1)},
        {"id": 2, "name": "Bob", "status": "Closed", "amount": 75, "created": date(2026, 6, 2)},
        {"id": 3, "name": "Charlie", "status": "Open", "amount": None, "created": date(2026, 6, 3)},
    ]


if __name__ == "__main__":
    unittest.main()
