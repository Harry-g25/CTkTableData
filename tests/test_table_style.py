from __future__ import annotations

import unittest

from CTkDataTable import TableStyle
from CTkDataTable.table_style import normalize_table_style


class TableStyleTests(unittest.TestCase):
    def test_normalize_table_style_accepts_aliases(self) -> None:
        style = normalize_table_style(
            {
                "fg_color": "#ffffff",
                "text": "#111827",
                "table_border": "#d1d5db",
                "badge_default_bg": "#e5e7eb",
            }
        )

        self.assertEqual(style.canvas_bg, "#ffffff")
        self.assertEqual(style.text_color, "#111827")
        self.assertEqual(style.border_color, "#d1d5db")
        self.assertEqual(style.badge_bg, "#e5e7eb")

    def test_normalize_table_style_rejects_unknown_options(self) -> None:
        with self.assertRaisesRegex(ValueError, "Unknown table style option"):
            normalize_table_style({"unknown": "#fff"})

    def test_normalize_table_style_rejects_negative_dimensions(self) -> None:
        with self.assertRaisesRegex(ValueError, "must not be negative"):
            normalize_table_style({"corner_radius": -1})

    def test_table_style_object_can_be_extended_with_keywords(self) -> None:
        style = normalize_table_style(TableStyle(header_bg="#f9fafb"), row_bg="#ffffff")

        self.assertEqual(style.header_bg, "#f9fafb")
        self.assertEqual(style.row_bg, "#ffffff")


if __name__ == "__main__":
    unittest.main()
