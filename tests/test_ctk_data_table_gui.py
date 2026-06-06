from __future__ import annotations

import threading
import time
import tkinter as tk
import unittest
from contextlib import suppress

import customtkinter as ctk

from CTkDataTable import CTkDataTable, TableRowEvent


def _make_root() -> ctk.CTk:
    try:
        root = ctk.CTk()
    except tk.TclError as error:
        raise unittest.SkipTest(f"Tk display is unavailable: {error}") from error
    root.withdraw()
    return root


def _destroy_root(root: ctk.CTk) -> None:
    with suppress(tk.TclError):
        for after_id in root.tk.call("after", "info"):
            root.after_cancel(after_id)
    root.destroy()


class CTkDataTableGuiTests(unittest.TestCase):
    def test_table_style_configures_colors_and_renderer_metrics(self) -> None:
        root = _make_root()
        try:
            table = CTkDataTable(
                root,
                columns=_columns(),
                data=_rows(),
                style={
                    "corner_radius": 14,
                    "border_width": 2,
                    "header_bg": "#101827",
                    "selected_text_color": "#ffffff",
                    "cell_padding_x": 16,
                    "badge_radius": 6,
                    "action_radius": 8,
                },
            )

            colors = table._theme_colors()

            self.assertEqual(table._table_corner_radius(), 14)
            self.assertEqual(table._table_border_width(), 2)
            self.assertEqual(colors["header_bg"], "#101827")
            self.assertEqual(colors["selected_text"], "#ffffff")
            self.assertEqual(table._renderer.cell_padding_x, 16)
            self.assertEqual(table._renderer.badge_radius, 6)
            self.assertEqual(table._renderer.action_radius, 8)

            table.configure_style(header_bg="#1f2937", action_radius=10)

            self.assertEqual(table._theme_colors()["header_bg"], "#1f2937")
            self.assertEqual(table._renderer.action_radius, 10)
        finally:
            _destroy_root(root)

    def test_widget_smoke_with_footer_filters_and_column_resize(self) -> None:
        root = _make_root()
        try:
            table = CTkDataTable(
                root,
                columns=_columns(),
                data=_rows(),
                resizable_columns=True,
                footer=True,
                summaries={"id": "count", "amount": "sum"},
                enable_style_hooks=True,
                row_style=lambda row: {"fg_color": "#fee2e2"} if row["status"] == "Closed" else None,
                cell_style=lambda _row, key, value: (
                    {"text_color": "#dc2626"} if key == "amount" and value < 100 else None
                ),
            )
            table.grid(row=0, column=0, sticky="nsew")
            root.update_idletasks()

            table.set_column_filter("status", {"type": "equals", "value": "Open"})
            table._set_column_width("name", 220)

            self.assertEqual([row["id"] for row in table._model.get_visible_rows()], [1, 3])
            self.assertEqual(table._model.require_column("name").width, 220)
            self.assertEqual(table.get_column_width("name"), 220)
        finally:
            _destroy_root(root)

    def test_public_view_index_helpers_use_current_view_order(self) -> None:
        root = _make_root()
        try:
            table = CTkDataTable(root, columns=_columns(), data=_rows())

            table.sort_by("amount", ascending=True)

            self.assertEqual(table.get_view_row(0)["id"], 2)
            self.assertEqual(table.source_index_for_view_index(0), 1)
            self.assertEqual(table.view_index_for_source_index(1), 0)

            table.update_view_row(0, {"id": 2, "name": "Bob", "status": "Closed", "amount": 70})
            self.assertEqual(table.get_row(1)["amount"], 70)

            table.set_data(_rows())
            table.sort_by("amount", ascending=True)
            table.delete_view_row(0)

            self.assertEqual([row["id"] for row in table.get_data()], [1, 3])
        finally:
            _destroy_root(root)

    def test_footer_summary_is_cached_during_vertical_scroll(self) -> None:
        root = _make_root()
        try:
            calls = [0]

            def summary(rows: list[dict[str, object]]) -> str:
                calls[0] += 1
                return str(len(rows))

            rows = [
                {"id": index, "name": f"Row {index}", "status": "Open", "amount": index}
                for index in range(30)
            ]
            table = CTkDataTable(
                root,
                columns=_columns(),
                data=rows,
                footer=True,
                summaries={"id": summary},
            )
            table.grid(row=0, column=0, sticky="nsew")
            table._canvas.configure(width=500, height=180)
            root.update_idletasks()
            table._canvas_width = 500
            table._canvas_height = 180

            calls[0] = 0
            table._invalidate_summary_cache()
            table._redraw(full=True)
            table._set_y_offset(table._row_height)

            self.assertEqual(calls[0], 1)
        finally:
            _destroy_root(root)

    def test_bottom_partial_row_is_not_rendered_or_hit_tested(self) -> None:
        root = _make_root()
        try:
            rows = [
                {"id": index, "name": f"Row {index}", "status": "Open", "amount": index}
                for index in range(10)
            ]
            table = CTkDataTable(root, columns=_columns(), data=rows)
            table.grid(row=0, column=0, sticky="nsew")
            root.update_idletasks()

            table._canvas_width = 500
            table._canvas_height = table._header_height + table._row_height * 2 + table._bottom_cap_height() + 20
            table._clamp_offsets()

            self.assertEqual(list(table._visible_row_range()), [0, 1])
            partial_row_y = table._header_height + table._row_height * 2 + 5
            self.assertIsNone(table._row_index_from_y(partial_row_y))
        finally:
            _destroy_root(root)

    def test_context_action_uses_table_row_event(self) -> None:
        root = _make_root()
        try:
            events: list[TableRowEvent] = []
            table = CTkDataTable(
                root,
                columns=_columns(),
                data=_rows(),
                context_menu=["copy"],
                on_context_action=events.append,
            )
            event = TableRowEvent(row=_rows()[0], source_index=0, view_index=0)

            table._invoke_context_action(event, "copy")

            self.assertEqual(events[0].action_key, "copy")
            self.assertEqual(events[0].row["id"], 1)
        finally:
            _destroy_root(root)

    def test_builtin_cell_types_render_and_link_clicks_dispatch_event(self) -> None:
        root = _make_root()
        try:
            events: list[TableRowEvent] = []
            table = CTkDataTable(
                root,
                columns=_feature_columns(),
                data=_feature_rows(),
                on_link_click=events.append,
            )
            table.grid(row=0, column=0, sticky="nsew")
            table._canvas.configure(width=760, height=180)
            root.update_idletasks()
            table._canvas_width = 760
            table._canvas_height = 180
            table._redraw(full=True)

            link_regions = [region for region in table._action_regions if region.kind == "link"]
            self.assertTrue(link_regions)
            x1, y1, x2, y2 = link_regions[0].bounds
            event = tk.Event()
            event.x = int((x1 + x2) / 2)
            event.y = int((y1 + y2) / 2)
            event.state = 0

            table._handle_click(event)

            self.assertEqual(events[0].row["id"], 1)
            self.assertEqual(events[0].column_key, "profile")
            self.assertEqual(events[0].action_key, "link")
            selected_row = table.get_selected_row()
            self.assertIsNotNone(selected_row)
            assert selected_row is not None
            self.assertEqual(selected_row["id"], 1)
        finally:
            _destroy_root(root)

    def test_checkbox_click_toggles_value_and_dispatches_event(self) -> None:
        root = _make_root()
        try:
            events: list[TableRowEvent] = []
            table = CTkDataTable(
                root,
                columns=_feature_columns(),
                data=_feature_rows(),
                on_checkbox_toggle=events.append,
            )
            table.grid(row=0, column=0, sticky="nsew")
            table._canvas.configure(width=760, height=180)
            root.update_idletasks()
            table._canvas_width = 760
            table._canvas_height = 180
            table._redraw(full=True)

            checkbox_regions = [region for region in table._action_regions if region.kind == "checkbox"]
            self.assertTrue(checkbox_regions)
            x1, y1, x2, y2 = checkbox_regions[0].bounds
            event = tk.Event()
            event.x = int((x1 + x2) / 2)
            event.y = int((y1 + y2) / 2)
            event.state = 0

            table._handle_click(event)

            updated_row = table.get_row(0)
            self.assertTrue(updated_row["approved"])
            self.assertEqual(events[0].row["id"], 1)
            self.assertTrue(events[0].row["approved"])
            self.assertEqual(events[0].column_key, "approved")
            self.assertEqual(events[0].action_key, "checkbox")
            selected_row = table.get_selected_row()
            self.assertIsNotNone(selected_row)
            assert selected_row is not None
            self.assertEqual(selected_row["id"], 1)
        finally:
            _destroy_root(root)

    def test_checkbox_double_click_toggles_back_and_checkbox_hover_uses_hand_cursor(self) -> None:
        root = _make_root()
        try:
            events: list[TableRowEvent] = []
            table = CTkDataTable(
                root,
                columns=_feature_columns(),
                data=_feature_rows(),
                on_checkbox_toggle=events.append,
            )
            table.grid(row=0, column=0, sticky="nsew")
            table._canvas.configure(width=760, height=180)
            root.update_idletasks()
            table._canvas_width = 760
            table._canvas_height = 180
            table._redraw(full=True)

            checkbox_regions = [region for region in table._action_regions if region.kind == "checkbox"]
            self.assertTrue(checkbox_regions)
            x1, y1, x2, y2 = checkbox_regions[0].bounds
            checkbox_event = tk.Event()
            checkbox_event.x = int((x1 + x2) / 2)
            checkbox_event.y = int((y1 + y2) / 2)
            checkbox_event.state = 0

            table._handle_motion(checkbox_event)
            self.assertEqual(table._table_canvas.cget("cursor"), "hand2")

            off_checkbox_event = tk.Event()
            off_checkbox_event.x = 4
            off_checkbox_event.y = checkbox_event.y
            off_checkbox_event.state = 0
            table._handle_motion(off_checkbox_event)
            self.assertEqual(table._table_canvas.cget("cursor"), "")

            table._handle_click(checkbox_event)
            self.assertTrue(table.get_row(0)["approved"])

            table._handle_double_click(checkbox_event)
            self.assertFalse(table.get_row(0)["approved"])
            self.assertEqual([event.row["approved"] for event in events], [True, False])
            self.assertEqual([event.action_key for event in events], ["checkbox", "checkbox"])
        finally:
            _destroy_root(root)

    def test_load_async_sets_data_on_tk_thread(self) -> None:
        root = _make_root()
        try:
            finished = threading.Event()
            table = CTkDataTable(root, columns=_columns(), data=[])
            table.grid(row=0, column=0, sticky="nsew")

            table.load_async(lambda: _rows(), on_success=lambda _rows: finished.set())

            deadline = time.monotonic() + 3
            while not finished.is_set() and time.monotonic() < deadline:
                root.update()
                time.sleep(0.01)

            self.assertTrue(finished.is_set())
            self.assertEqual(len(table.get_data()), 3)
            self.assertFalse(table._loading)
        finally:
            _destroy_root(root)


def _columns():
    return [
        {"key": "id", "title": "ID", "width": 80, "type": "number"},
        {"key": "name", "title": "Name", "width": 160},
        {"key": "status", "title": "Status", "width": 120, "type": "badge"},
        {"key": "amount", "title": "Amount", "width": 120, "type": "number"},
    ]


def _rows():
    return [
        {"id": 1, "name": "Alice", "status": "Open", "amount": 120},
        {"id": 2, "name": "Bob", "status": "Closed", "amount": 75},
        {"id": 3, "name": "Charlie", "status": "Open", "amount": 300},
    ]


def _feature_columns():
    return [
        {"key": "id", "title": "ID", "width": 70, "type": "number"},
        {"key": "approved", "title": "Approved", "width": 90, "type": "checkbox"},
        {"key": "cost", "title": "Cost", "width": 120, "type": "currency", "currency_symbol": "GBP "},
        {"key": "completion", "title": "Done", "width": 140, "type": "progress"},
        {"key": "profile", "title": "Profile", "width": 150, "type": "link"},
        {
            "key": "tags",
            "title": "Tags",
            "width": 200,
            "type": "pill_list",
            "pill_colors": {"Urgent": "#ef4444", "Finance": "#0ea5e9"},
        },
    ]


def _feature_rows():
    return [
        {
            "id": 1,
            "approved": False,
            "cost": 1200.5,
            "completion": 55,
            "profile": "Open profile",
            "tags": ["Urgent", "Finance"],
        },
        {"id": 2, "approved": True, "cost": 75, "completion": 15, "profile": "Open profile", "tags": "Ops, Review"},
    ]


if __name__ == "__main__":
    unittest.main()
