from __future__ import annotations

import unittest
from typing import Any

from CTkDataTable.table_column import Column, TableAction, TableColumn, normalize_columns


class TableColumnTests(unittest.TestCase):
    def test_normalize_columns_applies_simple_defaults(self) -> None:
        columns = normalize_columns(
            [
                {"key": "name", "title": "Name", "width": 160},
                {"key": "amount", "title": "Amount", "width": 120, "type": "number"},
                {"key": "actions", "title": "Actions", "width": 140, "type": "action"},
            ]
        )

        self.assertEqual(columns[0].align, "left")
        self.assertEqual(columns[1].align, "right")
        self.assertEqual(columns[2].align, "center")

    def test_duplicate_column_keys_raise_clear_error(self) -> None:
        with self.assertRaisesRegex(ValueError, "Duplicate column key 'name'"):
            normalize_columns(
                [
                    {"key": "name", "title": "Name", "width": 160},
                    {"key": "name", "title": "Display Name", "width": 180},
                ]
            )

    def test_action_definition_uses_documented_fields(self) -> None:
        action = TableAction.from_definition(
            {
                "key": "delete",
                "label": "Delete",
                "width": 72,
                "fg_color": "#fee2e2",
                "text_color": "#991b1b",
                "border_color": "#fecaca",
            }
        )

        self.assertEqual(action.key, "delete")
        self.assertEqual(action.label, "Delete")
        self.assertEqual(action.width, 72)
        self.assertEqual(action.fg_color, "#fee2e2")
        self.assertEqual(action.text_color, "#991b1b")
        self.assertEqual(action.border_color, "#fecaca")

    def test_badge_fallback_handler_must_be_callable(self) -> None:
        with self.assertRaisesRegex(TypeError, "badge fallback handler must be callable"):
            TableColumn.from_definition(
                {
                    "key": "status",
                    "title": "Status",
                    "width": 120,
                    "type": "badge",
                    "badge_fallback_handler": "#64748b",
                }
            )

    def test_formatter_must_be_callable(self) -> None:
        with self.assertRaisesRegex(TypeError, "formatter must be callable"):
            TableColumn.from_definition({"key": "name", "formatter": "{value}"})

    def test_number_format_must_be_string_or_callable(self) -> None:
        with self.assertRaisesRegex(TypeError, "number_format must be a format string or callable"):
            TableColumn.from_definition({"key": "amount", "type": "number", "number_format": 2})

    def test_builtin_feature_column_options_are_normalized(self) -> None:
        columns = normalize_columns(
            [
                Column("cost").title("Cost").currency(symbol="GBP "),
                Column("margin").title("Margin").percentage(format="{value:.1f}%", multiplier=100),
                Column("completion").progress(minimum=0, maximum=1, color="#22c55e", show_text=False),
                Column("profile").link(color="#2563eb"),
                Column("tags").pill_list(
                    colors={"Urgent": "#ef4444"},
                    fallback_color="#64748b",
                    text_color="#ffffff",
                ),
            ]
        )

        self.assertEqual(columns[0].type, "currency")
        self.assertEqual(columns[0].align, "right")
        self.assertEqual(columns[0].currency_symbol, "GBP ")
        self.assertEqual(columns[1].type, "percentage")
        self.assertEqual(columns[1].align, "right")
        self.assertEqual(columns[1].percentage_format, "{value:.1f}%")
        self.assertEqual(columns[1].percentage_multiplier, 100)
        self.assertEqual(columns[2].type, "progress")
        self.assertEqual(columns[2].align, "center")
        self.assertEqual(columns[2].progress_max, 1)
        self.assertFalse(columns[2].progress_show_text)
        self.assertEqual(columns[3].type, "link")
        self.assertEqual(columns[3].link_color, "#2563eb")
        self.assertEqual(columns[4].type, "pill_list")
        self.assertEqual(columns[4].pill_colors["Urgent"], "#ef4444")
        self.assertEqual(columns[4].pill_text_color, "#ffffff")

    def test_badge_colors_must_be_mapping(self) -> None:
        with self.assertRaisesRegex(TypeError, "badge_colors must be a mapping"):
            TableColumn.from_definition({"key": "status", "type": "badge", "badge_colors": ["Open"]})

    def test_pill_colors_must_be_mapping(self) -> None:
        with self.assertRaisesRegex(TypeError, "pill_colors must be a mapping"):
            TableColumn.from_definition({"key": "tags", "type": "pill_list", "pill_colors": ["Urgent"]})

    def test_progress_range_requires_maximum_greater_than_minimum(self) -> None:
        with self.assertRaisesRegex(ValueError, "progress_max must be greater than progress_min"):
            TableColumn.from_definition(
                {"key": "completion", "type": "progress", "progress_min": 10, "progress_max": 10}
            )

    def test_percentage_multiplier_must_be_greater_than_zero(self) -> None:
        with self.assertRaisesRegex(ValueError, "percentage_multiplier must be greater than zero"):
            TableColumn.from_definition({"key": "margin", "type": "percentage", "percentage_multiplier": 0})

    def test_metadata_must_be_mapping(self) -> None:
        with self.assertRaisesRegex(TypeError, "metadata must be a mapping"):
            TableColumn.from_definition({"key": "name", "metadata": ["private"]})

    def test_column_definition_must_be_mapping(self) -> None:
        definition: Any = "name"
        with self.assertRaisesRegex(TypeError, "Column definitions must be TableColumn objects or mappings"):
            TableColumn.from_definition(definition)

    def test_action_definition_must_be_supported_type(self) -> None:
        definition: Any = 123
        with self.assertRaisesRegex(TypeError, "Action definitions must be TableAction objects, mappings, or strings"):
            TableAction.from_definition(definition)


if __name__ == "__main__":
    unittest.main()
