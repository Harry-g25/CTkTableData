from __future__ import annotations

import unittest

from CTkDataTable.table_column import TableColumn
from CTkDataTable.table_renderer import TableRenderer


class TableRendererFormattingTests(unittest.TestCase):
    def test_percentage_values_use_configured_multiplier_and_format(self) -> None:
        column = TableColumn.from_definition(
            {
                "key": "margin",
                "title": "Margin",
                "width": 120,
                "type": "percentage",
                "percentage_format": "{value:.1f}%",
                "percentage_multiplier": 100,
            }
        )
        renderer = TableRenderer(object(), object(), object())

        self.assertEqual(renderer._format_value(0.1234, {"margin": 0.1234}, column), "12.3%")

    def test_percentage_format_falls_back_to_original_value_for_non_numeric_values(self) -> None:
        column = TableColumn.from_definition({"key": "margin", "title": "Margin", "width": 120, "type": "percentage"})
        renderer = TableRenderer(object(), object(), object())

        self.assertEqual(renderer._format_value("n/a", {"margin": "n/a"}, column), "n/a")


if __name__ == "__main__":
    unittest.main()
