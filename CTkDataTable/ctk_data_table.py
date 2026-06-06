"""A virtualized Canvas-rendered data table for CustomTkinter."""

from __future__ import annotations

import math
import queue
import threading
import tkinter as tk
import tkinter.font as tkfont
from bisect import bisect_left
from collections.abc import Callable, Iterable, Mapping, Sequence
from contextlib import suppress
from dataclasses import replace
from typing import Any, Literal, cast

import customtkinter as ctk

from .table_column import ColorValue, ColumnDefinition, TableAction, TableColumn, normalize_columns
from .table_events import TableRowEvent
from .table_model import ColumnFilter, RowData, TableModel
from .table_renderer import ActionRegion, TableRenderer
from .table_style import (
    TABLE_STYLE_COLOR_MAP,
    TableStyle,
    TableStyleDefinition,
    merge_table_style,
    normalize_table_style,
)

SortCallback = Callable[[str, bool], None]
SearchCallback = Callable[[str], None]
StyleDefinition = Mapping[str, Any]
RowStyleCallback = Callable[[RowData], StyleDefinition | None]
CellStyleCallback = Callable[[RowData, str, Any], StyleDefinition | None]
SummaryDefinition = str | Callable[[list[RowData]], Any]
AsyncFetchCallback = Callable[[], Iterable[Any]]
AsyncSuccessCallback = Callable[[list[dict[str, Any]]], None]
AsyncErrorCallback = Callable[[BaseException], None]


class CTkDataTable(ctk.CTkFrame):
    """Modern business data table rendered on a single tkinter Canvas."""

    _SHIFT_MASK = 0x0001
    _CONTROL_MASK = 0x0004

    def __init__(
        self,
        master: Any,
        columns: Sequence[ColumnDefinition],
        data: Iterable[Any] | None = None,
        *,
        row_height: int = 42,
        header_height: int = 44,
        footer_height: int = 38,
        font: Any | None = None,
        header_font: Any | None = None,
        horizontal_scroll: bool = False,
        multi_select: bool = False,
        searchable: bool = False,
        search_delay_ms: int = 0,
        resizable_columns: bool = False,
        min_column_width: int = 48,
        style: TableStyleDefinition | None = None,
        enable_style_hooks: bool = False,
        row_style: RowStyleCallback | None = None,
        cell_style: CellStyleCallback | None = None,
        context_menu: Sequence[TableAction | Mapping[str, Any] | str] | None = None,
        on_context_action: Callable[[TableRowEvent], None] | None = None,
        footer: bool = False,
        summaries: Mapping[str, SummaryDefinition] | None = None,
        empty_message: str = "No records to display",
        loading_message: str = "Loading records...",
        error_message: str = "Could not load records",
        on_row_click: Callable[[TableRowEvent], None] | None = None,
        on_row_double_click: Callable[[TableRowEvent], None] | None = None,
        on_cell_click: Callable[[TableRowEvent], None] | None = None,
        on_action_click: Callable[[TableRowEvent], None] | None = None,
        on_link_click: Callable[[TableRowEvent], None] | None = None,
        on_checkbox_toggle: Callable[[TableRowEvent], None] | None = None,
        on_sort: SortCallback | None = None,
        on_search: SearchCallback | None = None,
        **kwargs: Any,
    ) -> None:
        """Create a CTkDataTable.

        Columns are supplied as TableColumn instances or dictionaries. Row data
        can be dictionaries or common query row objects.
        """

        table_style = normalize_table_style(style)
        self._default_table_corner_radius = float(
            kwargs.pop("corner_radius", table_style.corner_radius if table_style.corner_radius is not None else 12)
        )
        self._default_table_border_width = float(
            kwargs.pop("border_width", table_style.border_width if table_style.border_width is not None else 1)
        )
        self._table_fg_color = kwargs.pop("fg_color", None)
        self._table_border_color = kwargs.pop("border_color", None)
        if table_style.surface_bg is not None:
            self._table_fg_color = table_style.surface_bg
        if table_style.border_color is not None:
            self._table_border_color = table_style.border_color
        kwargs.setdefault("corner_radius", 0)
        kwargs.setdefault("border_width", 0)
        kwargs.setdefault("fg_color", "transparent")
        super().__init__(master, **kwargs)

        if row_height < 28:
            raise ValueError("row_height must be at least 28 pixels.")
        if header_height < 32:
            raise ValueError("header_height must be at least 32 pixels.")
        if footer_height < 28:
            raise ValueError("footer_height must be at least 28 pixels.")
        if search_delay_ms < 0:
            raise ValueError("search_delay_ms must not be negative.")
        if min_column_width < 24:
            raise ValueError("min_column_width must be at least 24 pixels.")
        if not enable_style_hooks and (row_style is not None or cell_style is not None):
            raise ValueError("Set enable_style_hooks=True before passing row_style or cell_style callbacks.")

        self._columns = normalize_columns(columns)
        self._model = TableModel(self._columns)
        self._visible_columns_cache: list[TableColumn] = []
        self._column_edges_cache: tuple[float, ...] = ()
        self._column_edge_columns_cache: tuple[TableColumn, ...] = ()
        self._total_table_width_cache = 0
        self._row_height = row_height
        self._header_height = header_height
        self._footer_height = footer_height
        self._horizontal_scroll_enabled = horizontal_scroll
        self._multi_select = multi_select
        self._searchable = searchable
        self._search_delay_ms = search_delay_ms
        self._pending_search_after: str | None = None
        self._resizable_columns = resizable_columns
        self._resize_hit_width = 5
        self._resize_state: tuple[str, float, int] | None = None
        self._min_column_width = min_column_width
        self._enable_style_hooks = enable_style_hooks
        self._row_style_callback = row_style
        self._cell_style_callback = cell_style
        self._context_actions = tuple(
            TableAction.from_definition(action) for action in (context_menu or ())
        )
        self._context_action_callback = on_context_action
        self._footer_enabled = footer
        self._summaries = dict(summaries or {})
        self._summary_cache: dict[str, str] | None = None
        self._empty_message = empty_message
        self._loading_message = loading_message
        self._default_error_message = error_message
        self._error_message: str | None = None
        self._table_style = table_style
        self._theme_colors_cache: tuple[tuple[str, ...], dict[str, str]] | None = None

        self._row_click_callback = on_row_click
        self._row_double_click_callback = on_row_double_click
        self._cell_click_callback = on_cell_click
        self._action_click_callback = on_action_click
        self._link_click_callback = on_link_click
        self._checkbox_toggle_callback = on_checkbox_toggle
        self._sort_callback = on_sort
        self._search_callback = on_search

        self._loading = False
        self._load_generation = 0

        self._hovered_view_index: int | None = None
        self._rendered_view_indices: set[int] = set()
        self._action_regions: list[ActionRegion] = []
        self._action_regions_by_row: dict[int, list[ActionRegion]] = {}

        self._canvas_width = 1
        self._canvas_height = 1
        self._y_offset = 0.0
        self._x_offset = 0.0

        self._font = font if font is not None else self._make_font(size=13)
        if header_font is not None:
            self._header_font = header_font
        elif font is not None:
            self._header_font = font
        else:
            self._header_font = self._make_font(size=13, weight="bold")
        self._refresh_column_cache()

        self.grid_columnconfigure(0, weight=1)

        canvas_row = 0
        self._search_entry: ctk.CTkEntry | None = None
        if searchable:
            self.grid_rowconfigure(1, weight=1)
            canvas_row = 1
            self._search_entry = ctk.CTkEntry(self, placeholder_text="Search…")
            search_entry = self._search_entry
            assert search_entry is not None
            search_entry.grid(row=0, column=0, columnspan=2, sticky="ew", padx=8, pady=(8, 4))
            search_entry.bind("<KeyRelease>", lambda _e: self._queue_search(search_entry.get()))
        else:
            self.grid_rowconfigure(0, weight=1)

        self._table_canvas = tk.Canvas(self, bd=0, highlightthickness=0, takefocus=True)
        self._table_canvas.grid(row=canvas_row, column=0, sticky="nsew")

        self._vertical_scrollbar = ctk.CTkScrollbar(
            self,
            orientation="vertical",
            command=self._handle_vertical_scrollbar,
        )
        self._vertical_scrollbar.grid(row=canvas_row, column=1, sticky="ns", padx=(0, 2), pady=2)

        self._horizontal_scrollbar: ctk.CTkScrollbar | None = None
        if self._horizontal_scroll_enabled:
            self._horizontal_scrollbar = ctk.CTkScrollbar(
                self,
                orientation="horizontal",
                command=self._handle_horizontal_scrollbar,
            )
            self._horizontal_scrollbar.grid(row=canvas_row + 1, column=0, sticky="ew", padx=2, pady=(0, 2))

        self._renderer = TableRenderer(self._table_canvas, self._font, self._header_font, self._resolve_color)
        self._apply_renderer_style()
        self._apply_layout_insets()
        self._bind_events()
        self.set_data(data if data is not None else [])

    def set_data(self, data: Iterable[Any]) -> None:
        """Replace the dataset with row-like objects converted to dictionaries."""

        self._error_message = None
        self._model.set_data(data)
        self._hovered_view_index = None
        self._rebuild_view(preserve_scroll=False)

    def get_data(self) -> list[dict[str, Any]]:
        """Return a shallow copy of all source data rows."""

        return self._model.get_data()

    def get_columns(self) -> tuple[TableColumn, ...]:
        """Return the current normalized column definitions."""

        return self._columns

    def set_columns(self, columns: Sequence[ColumnDefinition]) -> None:
        """Replace column definitions while preserving compatible table state."""

        self._columns = normalize_columns(columns)
        self._model.set_columns(self._columns)
        self._refresh_column_cache()
        self._hovered_view_index = None
        self._invalidate_summary_cache()
        self._clamp_offsets()
        self._redraw(full=True)

    def set_column_width(self, column_key: str, width: int) -> None:
        """Set a column width programmatically."""

        self._set_column_width(column_key, width)

    def get_column_width(self, column_key: str) -> int:
        """Return the current width for a column key."""

        return self._model.require_column(column_key).width

    def refresh(self) -> None:
        """Refresh the current rendered view without changing data or selection."""

        self._clamp_offsets()
        self._redraw(full=True)

    def get_style(self) -> TableStyle:
        """Return the current table-wide style options."""

        return self._table_style

    def set_style(self, style: TableStyleDefinition | None = None, **kwargs: Any) -> None:
        """Replace table-wide style options and redraw the table.

        Pass a TableStyle, a mapping, keyword options, or any combination of a
        base style plus keyword overrides.
        """

        self._table_style = normalize_table_style(style, **kwargs)
        self._after_style_changed()

    def configure_style(self, style: TableStyleDefinition | None = None, **kwargs: Any) -> None:
        """Merge table-wide style options into the current style and redraw."""

        if style is None and not kwargs:
            return
        self._table_style = merge_table_style(self._table_style, style, **kwargs)
        self._after_style_changed()

    def clear(self) -> None:
        """Clear all rows from the table."""

        self.set_data([])

    def get_selected_row(self) -> dict[str, Any] | None:
        """Return the first selected row, or None when no row is selected."""

        rows = self.get_selected_rows()
        return rows[0] if rows else None

    def get_selected_rows(self) -> list[dict[str, Any]]:
        """Return selected rows as shallow copies."""

        return self._model.get_selected_rows()

    def get_selected_indices(self) -> list[int]:
        """Return selected source-data indices in current view order."""

        return self._model.get_selected_source_indices()

    def get_selected_view_indices(self) -> list[int]:
        """Return selected visible row indices in current view order."""

        return self._model.get_selected_view_indices()

    def get_row(self, index: int) -> dict[str, Any]:
        """Return a shallow copy of one source row."""

        return self._model.get_row(index)

    def get_view_row(self, view_index: int) -> dict[str, Any]:
        """Return a shallow copy of one row by current filtered/sorted view index."""

        return dict(self._model.row_for_view_index(view_index))

    def source_index_for_view_index(self, view_index: int) -> int:
        """Return the source-data index for a current view index."""

        return self._model.source_index_for_view_index(view_index)

    def view_index_for_source_index(self, source_index: int) -> int | None:
        """Return the current view index for a source-data index, if visible."""

        return self._model.view_index_for_source_index(source_index)

    def find_row_index(self, column_key: str, value: Any) -> int | None:
        """Return the first source row index whose column value matches value."""

        return self._model.find_source_index(column_key, value)

    def sort_by(self, column_key: str, ascending: bool = True) -> None:
        """Sort visible rows by a column key."""

        self._model.sort_by(column_key, bool(ascending))
        self._rebuild_view(preserve_scroll=False)
        if self._sort_callback is not None:
            self._sort_callback(column_key, bool(ascending))

    def search(self, query: str) -> None:
        """Filter rows by a case-insensitive query across all visible fields."""

        self._model.search(query)
        self._rebuild_view(preserve_scroll=False)
        if self._search_callback is not None:
            self._search_callback(self._model.filter_query)

    def filter(self, query: str) -> None:
        """Alias for :meth:`search` (backward compatibility)."""

        self.search(query)

    def set_column_filter(self, column_key: str, definition: ColumnFilter) -> None:
        """Set a column filter and refresh the visible rows."""

        self._model.set_column_filter(column_key, definition)
        self._rebuild_view(preserve_scroll=False)

    def clear_column_filter(self, column_key: str) -> None:
        """Clear one column filter and refresh the visible rows."""

        self._model.clear_column_filter(column_key)
        self._rebuild_view(preserve_scroll=False)

    def clear_column_filters(self) -> None:
        """Clear all column filters and refresh the visible rows."""

        self._model.clear_column_filters()
        self._rebuild_view(preserve_scroll=False)

    def get_column_filters(self) -> dict[str, ColumnFilter]:
        """Return a shallow copy of active column filters."""

        return self._model.column_filters

    def add_row(self, row: Any) -> int:
        """Append a row-like object and return its source index."""

        source_index = self._model.add_row(row)
        self._rebuild_view(preserve_scroll=True)
        return source_index

    def add_rows(self, rows: Iterable[Any]) -> list[int]:
        """Append multiple rows in a single rebuild and return their source indices."""

        source_indices = self._model.add_rows(rows)
        self._rebuild_view(preserve_scroll=True)
        return source_indices

    def update_row(self, index: int, row: Any) -> None:
        """Replace a source row by its integer index."""

        self._model.update_row(index, row)
        self._rebuild_view(preserve_scroll=True)

    def update_view_row(self, view_index: int, row: Any) -> None:
        """Replace a row by its current filtered/sorted view index."""

        self.update_row(self._model.source_index_for_view_index(view_index), row)

    def update_row_where(self, column_key: str, value: Any, new_row: Any) -> bool:
        """Replace the first row where *column_key* equals *value*.  Returns True if found."""

        updated = self._model.update_row_where(column_key, value, new_row)
        if updated:
            self._rebuild_view(preserve_scroll=True)
        return updated

    def delete_row(self, index: int) -> None:
        """Delete a source row by its integer index."""

        self._model.delete_row(index)
        self._rebuild_view(preserve_scroll=True)

    def delete_view_row(self, view_index: int) -> None:
        """Delete a row by its current filtered/sorted view index."""

        self.delete_row(self._model.source_index_for_view_index(view_index))

    def delete_row_where(self, column_key: str, value: Any) -> bool:
        """Delete the first row where *column_key* equals *value*.  Returns True if found."""

        deleted = self._model.delete_row_by_key(column_key, value)
        if deleted:
            self._rebuild_view(preserve_scroll=True)
        return deleted

    def delete_row_by_key(self, column_key: str, value: Any) -> bool:
        """Alias for :meth:`delete_row_where` (backward compatibility)."""

        return self.delete_row_where(column_key, value)

    def delete_selected_rows(self) -> int:
        """Delete all selected source rows and return the number removed."""

        count = self._model.delete_rows(self._model.get_selected_source_indices())
        if count:
            self._rebuild_view(preserve_scroll=True)
        return count

    def set_loading(self, state: bool) -> None:
        """Show or hide the loading state overlay."""

        self._loading = bool(state)
        if self._loading:
            self._error_message = None
        self._redraw(full=True)

    def set_error(self, message: str | None = None) -> None:
        """Show an error state. Pass None to use the default loading error message."""

        self._loading = False
        self._error_message = message or self._default_error_message
        self._redraw(full=True)

    def clear_error(self) -> None:
        """Hide the error state without changing table rows."""

        self._error_message = None
        self._redraw(full=True)

    def load_async(
        self,
        fetch_rows: AsyncFetchCallback,
        *,
        on_success: AsyncSuccessCallback | None = None,
        on_error: AsyncErrorCallback | None = None,
        clear_on_error: bool = False,
    ) -> threading.Thread:
        """Run a row loader in a background thread and update the table on the Tk thread."""

        self._load_generation += 1
        generation = self._load_generation
        self.set_loading(True)

        result_queue: queue.Queue[tuple[str, list[Any] | Exception]] = queue.Queue(maxsize=1)

        def run() -> None:
            try:
                rows = list(fetch_rows())
            except Exception as error:
                result_queue.put(("error", error))
                return
            result_queue.put(("success", rows))

        thread = threading.Thread(target=run, daemon=True)
        thread.start()
        self.after(10, lambda: self._poll_async_result(generation, result_queue, on_success, on_error, clear_on_error))
        return thread

    def _bind_events(self) -> None:
        self._table_canvas.bind("<Configure>", self._handle_configure)
        self._table_canvas.bind("<MouseWheel>", self._handle_mousewheel)
        self._table_canvas.bind("<Button-4>", self._handle_mousewheel)
        self._table_canvas.bind("<Button-5>", self._handle_mousewheel)
        self._table_canvas.bind("<Button-1>", self._handle_click)
        self._table_canvas.bind("<B1-Motion>", self._handle_drag)
        self._table_canvas.bind("<ButtonRelease-1>", self._handle_release)
        self._table_canvas.bind("<Button-3>", self._handle_context_menu)
        self._table_canvas.bind("<Control-Button-1>", self._handle_context_menu)
        self._table_canvas.bind("<Double-Button-1>", self._handle_double_click)
        self._table_canvas.bind("<Motion>", self._handle_motion)
        self._table_canvas.bind("<Leave>", self._handle_leave)
        self._table_canvas.bind("<KeyPress>", self._handle_keypress)

    def _make_font(self, *, size: int, weight: Literal["normal", "bold"] = "normal") -> Any:
        try:
            return ctk.CTkFont(size=size, weight=weight)
        except Exception:
            font = tkfont.nametofont("TkDefaultFont").copy()
            font.configure(size=size, weight=weight)
            return font

    def _handle_configure(self, event: tk.Event[Any]) -> None:
        self._canvas_width = max(1, int(event.width))
        self._canvas_height = max(1, int(event.height))
        self._clamp_offsets()
        self._redraw(full=True)

    def _handle_vertical_scrollbar(self, *args: str) -> None:
        if not args:
            return
        if args[0] == "moveto" and len(args) >= 2:
            self._set_y_offset(float(args[1]) * self._total_body_height())
        elif args[0] == "scroll" and len(args) >= 3:
            amount = int(args[1])
            unit = args[2]
            step = self._row_height if unit == "units" else max(self._row_height, self._body_height())
            self._set_y_offset(self._y_offset + amount * step)

    def _handle_horizontal_scrollbar(self, *args: str) -> None:
        if not args:
            return
        if args[0] == "moveto" and len(args) >= 2:
            self._set_x_offset(float(args[1]) * self._total_table_width())
        elif args[0] == "scroll" and len(args) >= 3:
            amount = int(args[1])
            unit = args[2]
            step = 40 if unit == "units" else max(80, self._canvas_width)
            self._set_x_offset(self._x_offset + amount * step)

    def _handle_mousewheel(self, event: tk.Event[Any]) -> str:
        if getattr(event, "num", None) == 4:
            units: float = -1
        elif getattr(event, "num", None) == 5:
            units = 1
        else:
            delta = getattr(event, "delta", 0)
            units = -delta / 120 if delta else 0
            if units and abs(units) < 1:
                units = -1 if delta > 0 else 1

        if self._horizontal_scroll_enabled and getattr(event, "state", 0) & self._SHIFT_MASK:
            self._set_x_offset(self._x_offset + units * 40)
        else:
            self._set_y_offset(self._y_offset + units * self._row_height)
        return "break"

    def _handle_click(self, event: tk.Event[Any]) -> str | None:
        self._table_canvas.focus_set()
        if event.y < self._header_height:
            resize_column = self._resize_column_from_x(event.x)
            if resize_column is not None:
                self._resize_state = (resize_column.key, float(event.x), resize_column.width)
                return "break"
            column = self._column_from_x(event.x)
            if column is not None and column.sortable:
                ascending = True
                if self._model.sort_state is not None and self._model.sort_state[0] == column.key:
                    ascending = not self._model.sort_state[1]
                self.sort_by(column.key, ascending)
            return "break"

        if self._loading:
            return "break"

        view_index = self._row_index_from_y(event.y)
        if view_index is None:
            return None

        action_region = self._hit_action(event.x, event.y)
        row = self._row_for_view_index(view_index)
        source_index = self._model.source_index_for_view_index(view_index)
        if action_region is not None and action_region.kind == "action":
            if self._action_click_callback is not None:
                self._action_click_callback(
                    TableRowEvent(
                        row=dict(row),
                        source_index=source_index,
                        view_index=view_index,
                        column_key=action_region.column_key,
                        action_key=action_region.action_key,
                    )
                )
            return "break"
        if action_region is not None and action_region.kind == "checkbox":
            self._toggle_checkbox(view_index, action_region.column_key, event)
            return "break"
        if action_region is not None and action_region.kind == "link":
            self._select_view_index(view_index, event)
            if self._link_click_callback is not None:
                self._link_click_callback(
                    TableRowEvent(
                        row=dict(row),
                        source_index=source_index,
                        view_index=view_index,
                        column_key=action_region.column_key,
                        action_key=action_region.action_key,
                    )
                )
                return "break"

        column = self._column_from_x(event.x)
        self._select_view_index(view_index, event)
        if column is not None and self._cell_click_callback is not None:
            self._cell_click_callback(
                TableRowEvent(row=dict(row), source_index=source_index, view_index=view_index, column_key=column.key)
            )
        if self._row_click_callback is not None:
            self._row_click_callback(TableRowEvent(row=dict(row), source_index=source_index, view_index=view_index))
        return "break"

    def _handle_drag(self, event: tk.Event[Any]) -> str | None:
        if self._resize_state is None:
            return None
        column_key, start_x, start_width = self._resize_state
        width = max(self._min_column_width, round(start_width + float(event.x) - start_x))
        self._set_column_width(column_key, width)
        return "break"

    def _handle_release(self, _event: tk.Event[Any]) -> str | None:
        if self._resize_state is None:
            return None
        self._resize_state = None
        self._update_header_cursor(None)
        return "break"

    def _handle_context_menu(self, event: tk.Event[Any]) -> str | None:
        if not self._context_actions or self._loading or self._error_message is not None:
            return None
        view_index = self._row_index_from_y(event.y)
        if view_index is None:
            return None
        self._table_canvas.focus_set()
        self._select_view_index(view_index, event)
        row_event = self._event_for_view_index(view_index)

        menu = tk.Menu(self._table_canvas, tearoff=0)
        for action in self._context_actions:
            menu.add_command(
                label=action.label,
                command=self._context_command(row_event, action.key),
            )
        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()
        return "break"

    def _context_command(self, row_event: TableRowEvent, action_key: str) -> Callable[[], None]:
        return lambda: self._invoke_context_action(row_event, action_key)

    def _handle_double_click(self, event: tk.Event[Any]) -> str | None:
        if event.y < self._header_height or self._loading:
            return "break"
        action_region = self._hit_action(event.x, event.y)
        if action_region is not None and action_region.kind == "checkbox":
            view_index = self._row_index_from_y(event.y)
            if view_index is not None:
                self._toggle_checkbox(view_index, action_region.column_key, event)
            return "break"
        if action_region is not None and (action_region.kind == "action" or self._link_click_callback is not None):
            return "break"
        view_index = self._row_index_from_y(event.y)
        if view_index is None:
            return None
        if self._row_double_click_callback is not None:
            self._row_double_click_callback(self._event_for_view_index(view_index))
        return "break"

    def _handle_keypress(self, event: tk.Event[Any]) -> str | None:
        if self._loading or not self._model.view_indices:
            return None

        keysym = getattr(event, "keysym", "")
        focused_view_index = self._model.focused_view_index()

        page_size = max(1, self._body_height() // self._row_height)
        last_index = len(self._model.view_indices) - 1
        target_index: int | None = None

        if focused_view_index is None:
            if keysym in {"End", "Prior"}:
                target_index = last_index
            elif keysym in {"Up", "Down", "Next", "Home"}:
                target_index = 0
            else:
                return None
        elif keysym == "Up":
            target_index = max(0, focused_view_index - 1)
        elif keysym == "Down":
            target_index = min(last_index, focused_view_index + 1)
        elif keysym == "Prior":
            target_index = max(0, focused_view_index - page_size)
        elif keysym == "Next":
            target_index = min(last_index, focused_view_index + page_size)
        elif keysym == "Home":
            target_index = 0
        elif keysym == "End":
            target_index = last_index
        elif keysym in {"Return", "KP_Enter"}:
            if self._row_double_click_callback is not None:
                self._row_double_click_callback(self._event_for_view_index(focused_view_index))
            return "break"
        else:
            return None

        state = getattr(event, "state", 0)
        changed = self._model.select_view_index(
            target_index,
            multi_select=self._multi_select,
            shift=bool(state & self._SHIFT_MASK),
            control=False,
        )
        self._scroll_view_index_into_view(target_index)
        self._redraw_changed_sources(changed)
        return "break"

    def _event_for_view_index(
        self,
        view_index: int,
        *,
        column_key: str | None = None,
        action_key: str | None = None,
    ) -> TableRowEvent:
        source_index = self._model.source_index_for_view_index(view_index)
        return TableRowEvent(
            row=dict(self._row_for_view_index(view_index)),
            source_index=source_index,
            view_index=view_index,
            column_key=column_key,
            action_key=action_key,
        )

    def _toggle_checkbox(self, view_index: int, column_key: str, event: tk.Event[Any]) -> None:
        source_index = self._model.source_index_for_view_index(view_index)
        row = dict(self._row_for_view_index(view_index))
        row[column_key] = not bool(row.get(column_key))

        self._select_view_index(view_index, event)
        self._model.update_row(source_index, row)
        current_view_index = self._model.view_index_for_source_index(source_index)
        self._rebuild_view(preserve_scroll=True)

        if self._checkbox_toggle_callback is not None:
            self._checkbox_toggle_callback(
                TableRowEvent(
                    row=dict(row),
                    source_index=source_index,
                    view_index=current_view_index if current_view_index is not None else view_index,
                    column_key=column_key,
                    action_key="checkbox",
                )
            )

    def _handle_motion(self, event: tk.Event[Any]) -> None:
        if self._resize_state is not None:
            return
        if event.y < self._header_height:
            self._update_header_cursor(self._resize_column_from_x(event.x))
        else:
            action_region = None if self._loading else self._hit_action(event.x, event.y)
            cursor = "hand2" if action_region is not None and action_region.kind == "checkbox" else ""
            self._update_canvas_cursor(cursor)
        view_index = None if self._loading else self._row_index_from_y(event.y)
        if view_index == self._hovered_view_index:
            return
        old_index = self._hovered_view_index
        self._hovered_view_index = view_index
        if old_index is not None:
            self._redraw_row(old_index)
        if view_index is not None:
            self._redraw_row(view_index)
        self._refresh_action_regions()
        self._table_canvas.tag_raise("header")

    def _handle_leave(self, _event: tk.Event[Any]) -> None:
        if self._resize_state is None:
            self._update_header_cursor(None)
        if self._hovered_view_index is None:
            return
        old_index = self._hovered_view_index
        self._hovered_view_index = None
        self._redraw_row(old_index)
        self._refresh_action_regions()
        self._table_canvas.tag_raise("header")

    def _select_view_index(self, view_index: int, event: tk.Event[Any]) -> None:
        state = getattr(event, "state", 0)
        changed = self._model.select_view_index(
            view_index,
            multi_select=self._multi_select,
            shift=bool(state & self._SHIFT_MASK),
            control=bool(state & self._CONTROL_MASK),
        )
        self._redraw_changed_sources(changed)

    def _set_column_width(self, column_key: str, width: int) -> None:
        columns = tuple(
            replace(column, width=max(self._min_column_width, int(width))) if column.key == column_key else column
            for column in self._columns
        )
        if columns == self._columns:
            return
        self._columns = columns
        self._model.set_columns(columns, rebuild=False, clear_search_cache=False)
        self._refresh_column_cache()
        self._clamp_offsets()
        self._redraw(full=True)

    def _resize_column_from_x(self, x: float) -> TableColumn | None:
        if not self._resizable_columns:
            return None
        content_x = x + self._x_offset
        edge_index = bisect_left(self._column_edges_cache, content_x)
        for index in {edge_index - 1, edge_index}:
            if (
                0 <= index < len(self._column_edges_cache)
                and abs(content_x - self._column_edges_cache[index]) <= self._resize_hit_width
            ):
                return self._column_edge_columns_cache[index]
        return None

    def _update_header_cursor(self, resize_column: TableColumn | None) -> None:
        cursor = "sb_h_double_arrow" if resize_column is not None else ""
        self._update_canvas_cursor(cursor)

    def _update_canvas_cursor(self, cursor: str) -> None:
        try:
            if self._table_canvas.cget("cursor") != cursor:
                self._table_canvas.configure(cursor=cursor)
        except tk.TclError:
            return

    def _invoke_context_action(self, row_event: TableRowEvent, action_key: str) -> None:
        if self._context_action_callback is None:
            return
        self._context_action_callback(
            TableRowEvent(
                row=dict(row_event.row),
                source_index=row_event.source_index,
                view_index=row_event.view_index,
                column_key=row_event.column_key,
                action_key=action_key,
            )
        )

    def _queue_search(self, query: str) -> None:
        if self._pending_search_after is not None:
            with suppress(tk.TclError):
                self.after_cancel(self._pending_search_after)
            self._pending_search_after = None
        if self._search_delay_ms <= 0:
            self.search(query)
            return
        self._pending_search_after = self.after(self._search_delay_ms, lambda: self._run_queued_search(query))

    def _run_queued_search(self, query: str) -> None:
        self._pending_search_after = None
        self.search(query)

    def _finish_async_success(
        self,
        generation: int,
        rows: list[Any],
        on_success: AsyncSuccessCallback | None,
    ) -> None:
        if generation != self._load_generation:
            return
        self._loading = False
        self.set_data(rows)
        if on_success is not None:
            on_success(self.get_data())

    def _poll_async_result(
        self,
        generation: int,
        result_queue: queue.Queue[tuple[str, list[Any] | Exception]],
        on_success: AsyncSuccessCallback | None,
        on_error: AsyncErrorCallback | None,
        clear_on_error: bool,
    ) -> None:
        if generation != self._load_generation:
            return
        try:
            kind, payload = result_queue.get_nowait()
        except queue.Empty:
            self.after(
                10,
                lambda: self._poll_async_result(generation, result_queue, on_success, on_error, clear_on_error),
            )
            return
        if kind == "success":
            self._finish_async_success(generation, cast(list[Any], payload), on_success)
        else:
            self._finish_async_error(generation, cast(Exception, payload), on_error, clear_on_error)

    def _finish_async_error(
        self,
        generation: int,
        error: Exception,
        on_error: AsyncErrorCallback | None,
        clear_on_error: bool,
    ) -> None:
        if generation != self._load_generation:
            return
        if clear_on_error:
            self.clear()
        self.set_error(str(error) or self._default_error_message)
        if on_error is not None:
            on_error(error)

    def _style_for_row(self, row: RowData) -> StyleDefinition | None:
        if self._row_style_callback is None:
            return None
        try:
            style = self._row_style_callback(dict(row))
        except Exception as error:
            raise RuntimeError(f"row_style callback failed: {error}") from error
        if style is not None and not isinstance(style, Mapping):
            raise TypeError("row_style must return a mapping or None.")
        return style

    def _styles_for_cells(self, row: RowData) -> dict[str, StyleDefinition]:
        if self._cell_style_callback is None:
            return {}
        styles: dict[str, StyleDefinition] = {}
        row_copy = dict(row)
        for column in self._visible_columns():
            try:
                style = self._cell_style_callback(row_copy, column.key, row.get(column.key))
            except Exception as error:
                raise RuntimeError(f"cell_style callback failed for column '{column.key}': {error}") from error
            if style is not None:
                if not isinstance(style, Mapping):
                    raise TypeError("cell_style must return a mapping or None.")
                styles[column.key] = style
        return styles

    def _summary_values(self) -> dict[str, str]:
        if not self._footer_enabled:
            return {}
        if self._summary_cache is None:
            rows = [self._model.source_data[index] for index in self._model.view_indices]
            self._summary_cache = {
                column_key: self._summary_value(column_key, definition, rows)
                for column_key, definition in self._summaries.items()
            }
        return self._summary_cache

    def _summary_value(self, column_key: str, definition: SummaryDefinition, rows: list[RowData]) -> str:
        if callable(definition):
            try:
                return str(definition([dict(row) for row in rows]))
            except Exception as error:
                raise RuntimeError(f"Summary callback failed for column '{column_key}': {error}") from error
        name = str(definition).casefold()
        values = [row.get(column_key) for row in rows]
        if name == "count":
            return str(len(rows))
        numbers = self._numeric_values(values)
        if name == "sum":
            return self._format_summary_number(sum(numbers)) if numbers else ""
        if name in {"avg", "average"}:
            return self._format_summary_number(sum(numbers) / len(numbers)) if numbers else ""
        if name == "min":
            return self._format_summary_number(min(numbers)) if numbers else ""
        if name == "max":
            return self._format_summary_number(max(numbers)) if numbers else ""
        return str(definition)

    def _numeric_values(self, values: Iterable[Any]) -> list[float]:
        numbers: list[float] = []
        for value in values:
            if value is None or value == "":
                continue
            try:
                numbers.append(float(str(value).replace(",", "")))
            except (TypeError, ValueError):
                continue
        return numbers

    def _format_summary_number(self, value: float) -> str:
        if value.is_integer():
            return str(int(value))
        return f"{value:,.2f}"

    def _invalidate_summary_cache(self) -> None:
        self._summary_cache = None

    def _redraw_changed_sources(self, source_indices: set[int]) -> None:
        for source_index in source_indices:
            changed_view_index = self._view_index_for_source_index(source_index)
            if changed_view_index is not None:
                self._redraw_row(changed_view_index)

    def _rebuild_view(self, *, preserve_scroll: bool) -> None:
        old_y = self._y_offset
        self._invalidate_summary_cache()

        if not preserve_scroll:
            self._y_offset = 0.0
        else:
            self._y_offset = old_y

        self._clamp_offsets()
        self._redraw(full=True)

    def _redraw(
        self,
        *,
        full: bool,
        previous_y_offset: float | None = None,
        redraw_fixed: bool = True,
    ) -> None:
        colors = self._theme_colors()
        self._table_canvas.configure(background=colors["canvas_bg"])
        self._update_scrollregion()
        self._sync_scrollbars()
        self._apply_action_colors(colors)

        if full:
            self._table_canvas.delete("all")
            self._rendered_view_indices.clear()
            self._action_regions_by_row.clear()
            self._draw_table_surface(colors)
            self._draw_header(colors)
        else:
            self._table_canvas.delete("state")
            if previous_y_offset is not None:
                delta_y = previous_y_offset - self._y_offset
                for row_index in list(self._rendered_view_indices):
                    self._table_canvas.move(f"row_{row_index}", 0, delta_y)
                self._move_action_regions(delta_y)

        if self._loading or self._error_message is not None or not self._model.view_indices:
            self._table_canvas.delete("body")
            self._rendered_view_indices.clear()
            self._draw_state(colors)
            self._table_canvas.tag_raise("header")
            if redraw_fixed:
                self._draw_footer(colors)
                self._draw_table_chrome(colors)
            else:
                self._raise_fixed_layers()
            self._action_regions.clear()
            self._action_regions_by_row.clear()
            return

        self._table_canvas.delete("state")
        self._draw_visible_rows(colors)
        self._refresh_action_regions()
        self._table_canvas.tag_raise("header")
        if redraw_fixed:
            self._draw_footer(colors)
            self._draw_table_chrome(colors)
        else:
            self._raise_fixed_layers()

    def _draw_table_surface(self, colors: Mapping[str, str]) -> None:
        self._renderer.draw_surface(
            canvas_width=self._canvas_width,
            canvas_height=self._canvas_height,
            radius=self._table_corner_radius(),
            colors=colors,
        )

    def _draw_table_chrome(self, colors: Mapping[str, str]) -> None:
        self._renderer.draw_chrome(
            canvas_width=self._canvas_width,
            canvas_height=self._canvas_height,
            radius=self._table_corner_radius(),
            border_width=self._table_border_width(),
            bottom_cap_height=self._bottom_cap_height(),
            colors=colors,
        )

    def _draw_header(self, colors: Mapping[str, str]) -> None:
        sort_key = self._model.sort_state[0] if self._model.sort_state else None
        sort_ascending = self._model.sort_state[1] if self._model.sort_state else True
        self._renderer.draw_header(
            self._visible_columns(),
            x_offset=self._x_offset,
            canvas_width=self._canvas_width,
            header_height=self._header_height,
            radius=self._table_corner_radius(),
            sort_key=sort_key,
            sort_ascending=sort_ascending,
            filtered_column_keys=set(self._model.column_filters),
            colors=colors,
        )

    def _draw_footer(self, colors: Mapping[str, str]) -> None:
        if not self._footer_enabled:
            self._table_canvas.delete("footer")
            return
        self._renderer.draw_footer(
            self._visible_columns(),
            self._summary_values(),
            x_offset=self._x_offset,
            canvas_width=self._canvas_width,
            footer_top=self._footer_top(),
            footer_height=self._footer_height,
            radius=self._table_corner_radius(),
            colors=colors,
        )
        self._table_canvas.tag_raise("footer")

    def _raise_fixed_layers(self) -> None:
        self._table_canvas.tag_raise("header")
        if self._footer_enabled:
            self._table_canvas.tag_raise("footer")
        self._table_canvas.tag_raise("table_chrome")

    def _draw_visible_rows(self, colors: Mapping[str, str]) -> None:
        visible_indices = set(self._visible_row_range())
        for row_index in list(self._rendered_view_indices):
            if row_index not in visible_indices:
                self._table_canvas.delete(f"row_{row_index}")
                self._rendered_view_indices.remove(row_index)
                self._action_regions_by_row.pop(row_index, None)

        for row_index in sorted(visible_indices):
            if row_index not in self._rendered_view_indices:
                self._draw_row(row_index, colors)

    def _redraw_row(self, row_index: int) -> None:
        if row_index < 0 or row_index >= len(self._model.view_indices):
            return
        if row_index not in self._visible_row_range():
            return
        colors = self._theme_colors()
        self._apply_action_colors(colors)
        self._table_canvas.delete(f"row_{row_index}")
        self._rendered_view_indices.discard(row_index)
        self._action_regions_by_row.pop(row_index, None)
        self._draw_row(row_index, colors)
        self._refresh_action_regions()
        self._table_canvas.tag_raise("header")
        self._raise_fixed_layers()

    def _draw_row(self, row_index: int, colors: Mapping[str, str]) -> None:
        source_index = self._model.source_index_for_view_index(row_index)
        row = self._model.row_for_view_index(row_index)
        row_style = self._style_for_row(row) if self._enable_style_hooks else None
        cell_styles = self._styles_for_cells(row) if self._enable_style_hooks else None
        regions = self._renderer.draw_row(
            row_index,
            row,
            self._visible_columns(),
            y=self._row_y(row_index),
            row_height=self._row_height,
            x_offset=self._x_offset,
            canvas_width=self._canvas_width,
            selected=source_index in self._model.selected_source_indices,
            hovered=row_index == self._hovered_view_index,
            row_style=row_style,
            cell_styles=cell_styles,
            colors=colors,
        )
        self._action_regions_by_row[row_index] = regions
        self._rendered_view_indices.add(row_index)

    def _draw_state(self, colors: Mapping[str, str]) -> None:
        message = self._loading_message if self._loading else self._empty_message
        if self._error_message is not None:
            message = self._error_message
        elif (
            not self._loading
            and (self._model.filter_query.strip() or self._model.column_filters)
            and self._model.source_data
        ):
            message = "No matching records"

        body_top = self._header_height
        body_height = self._body_height()
        self._table_canvas.create_rectangle(
            0,
            body_top,
            self._canvas_width,
            self._footer_top(),
            fill=colors["surface_bg"],
            outline="",
            tags=("state",),
        )
        center_y = body_top + body_height / 2
        if self._loading:
            indicator_width = min(160, max(80, self._canvas_width * 0.3))
            self._table_canvas.create_rectangle(
                (self._canvas_width - indicator_width) / 2,
                center_y + 20,
                (self._canvas_width + indicator_width) / 2,
                center_y + 24,
                fill=colors["loading_indicator"],
                outline="",
                tags=("state", "loading_indicator"),
            )
        self._table_canvas.create_text(
            self._canvas_width / 2,
            center_y,
            text=message,
            fill=colors["muted_text"],
            font=self._font,
            anchor="center",
            tags=("state", "state_text"),
        )

    def _refresh_action_regions(self) -> None:
        self._action_regions = [
            region
            for row_index in self._rendered_view_indices
            for region in self._action_regions_by_row.get(row_index, [])
        ]

    def _move_action_regions(self, delta_y: float) -> None:
        if not delta_y:
            return
        moved_by_row: dict[int, list[ActionRegion]] = {}
        for row_index, regions in self._action_regions_by_row.items():
            moved_regions: list[ActionRegion] = []
            for region in regions:
                x1, y1, x2, y2 = region.bounds
                moved_regions.append(
                    ActionRegion(
                        row_index=region.row_index,
                        column_key=region.column_key,
                        action_key=region.action_key,
                        bounds=(x1, y1 + delta_y, x2, y2 + delta_y),
                        kind=region.kind,
                    )
                )
            moved_by_row[row_index] = moved_regions
        self._action_regions_by_row = moved_by_row

    def _hit_action(self, x: float, y: float) -> ActionRegion | None:
        for region in self._action_regions:
            x1, y1, x2, y2 = region.bounds
            if x1 <= x <= x2 and y1 <= y <= y2:
                return region
        return None

    def _visible_row_range(self) -> range:
        body_height = self._body_height()
        if body_height <= 0 or not self._model.view_indices:
            return range(0)
        start = max(0, int(self._y_offset // self._row_height))
        end = min(len(self._model.view_indices), int((self._y_offset + body_height) // self._row_height))
        return range(start, end)

    def _row_y(self, row_index: int) -> float:
        return self._header_height + row_index * self._row_height - self._y_offset

    def _scroll_view_index_into_view(self, view_index: int) -> None:
        row_top = view_index * self._row_height
        row_bottom = row_top + self._row_height
        viewport_top = self._y_offset
        viewport_bottom = self._y_offset + self._body_height()

        if row_top < viewport_top:
            self._set_y_offset(float(row_top))
        elif row_bottom > viewport_bottom:
            self._set_y_offset(float(row_bottom - self._body_height()))

    def _row_index_from_y(self, y: float) -> int | None:
        if y < self._header_height or y > self._footer_top():
            return None
        row_index = int((y - self._header_height + self._y_offset) // self._row_height)
        row_bottom = (row_index + 1) * self._row_height
        if row_bottom > self._y_offset + self._body_height():
            return None
        if 0 <= row_index < len(self._model.view_indices):
            return row_index
        return None

    def _row_for_view_index(self, view_index: int) -> RowData:
        return self._model.row_for_view_index(view_index)

    def _view_index_for_source_index(self, source_index: int) -> int | None:
        return self._model.view_index_for_source_index(source_index)

    def _column_from_x(self, x: float) -> TableColumn | None:
        content_x = x + self._x_offset
        if content_x < 0:
            return None
        index = bisect_left(self._column_edges_cache, content_x)
        if 0 <= index < len(self._column_edge_columns_cache):
            return self._column_edge_columns_cache[index]
        return None

    def _visible_columns(self) -> list[TableColumn]:
        return self._visible_columns_cache

    def _refresh_column_cache(self) -> None:
        visible_columns = [column for column in self._columns if column.visible]
        edges: list[float] = []
        cursor = 0.0
        for column in visible_columns:
            cursor += column.width
            edges.append(cursor)
        self._visible_columns_cache = visible_columns
        self._column_edges_cache = tuple(edges)
        self._column_edge_columns_cache = tuple(visible_columns)
        self._total_table_width_cache = int(cursor)

    def _set_y_offset(self, value: float) -> None:
        old_offset = self._y_offset
        self._y_offset = min(max(0.0, value), self._max_y_offset())
        if self._y_offset != old_offset:
            self._sync_scrollbars()
            self._redraw(full=False, previous_y_offset=old_offset, redraw_fixed=False)

    def _set_x_offset(self, value: float) -> None:
        old_offset = self._x_offset
        self._x_offset = min(max(0.0, value), self._max_x_offset())
        if self._x_offset != old_offset:
            self._sync_scrollbars()
            self._redraw(full=True)

    def _clamp_offsets(self) -> None:
        self._y_offset = min(max(0.0, self._y_offset), self._max_y_offset())
        self._x_offset = min(max(0.0, self._x_offset), self._max_x_offset())

    def _update_scrollregion(self) -> None:
        self._table_canvas.configure(
            scrollregion=(
                0,
                0,
                max(self._canvas_width, self._total_table_width()),
                self._header_height + self._total_body_height() + self._active_footer_height(),
            )
        )

    def _sync_scrollbars(self) -> None:
        total_body_height = self._total_body_height()
        body_height = self._body_height()
        if total_body_height <= body_height or total_body_height <= 0:
            self._vertical_scrollbar.set(0, 1)
        else:
            first = self._y_offset / total_body_height
            last = min(1.0, (self._y_offset + body_height) / total_body_height)
            self._vertical_scrollbar.set(first, last)

        if self._horizontal_scrollbar is not None:
            total_width = self._total_table_width()
            if total_width <= self._canvas_width or total_width <= 0:
                self._horizontal_scrollbar.set(0, 1)
            else:
                first = self._x_offset / total_width
                last = min(1.0, (self._x_offset + self._canvas_width) / total_width)
                self._horizontal_scrollbar.set(first, last)

    def _body_height(self) -> int:
        return max(0, self._footer_top() - self._header_height)

    def _active_footer_height(self) -> int:
        return self._footer_height if self._footer_enabled else 0

    def _footer_top(self) -> int:
        return max(self._header_height, self._canvas_height - self._active_footer_height() - self._bottom_cap_height())

    def _total_body_height(self) -> int:
        return len(self._model.view_indices) * self._row_height

    def _total_table_width(self) -> int:
        return self._total_table_width_cache

    def _max_y_offset(self) -> float:
        return max(0.0, self._total_body_height() - self._body_height())

    def _max_x_offset(self) -> float:
        if not self._horizontal_scroll_enabled:
            return 0.0
        return max(0.0, self._total_table_width() - self._canvas_width)

    def _after_style_changed(self) -> None:
        self._theme_colors_cache = None
        self._apply_frame_style()
        self._apply_renderer_style()
        self._apply_layout_insets()
        self._redraw(full=True)

    def _apply_layout_insets(self) -> None:
        if not hasattr(self, "_table_canvas"):
            return
        scrollbar_gap = self._scrollbar_gap()
        self._table_canvas.grid_configure(padx=0, pady=0)
        self._vertical_scrollbar.grid_configure(padx=(scrollbar_gap, 0), pady=4)
        if self._horizontal_scrollbar is not None:
            self._horizontal_scrollbar.grid_configure(padx=(0, scrollbar_gap), pady=(scrollbar_gap, 0))

    def _scrollbar_gap(self) -> int:
        radius = self._table_corner_radius()
        if radius <= 0:
            return 0
        return max(4, min(8, math.ceil(radius / 2)))

    def _bottom_cap_height(self) -> int:
        if self._footer_enabled:
            return 0
        radius = self._table_corner_radius()
        if radius <= 0:
            return 0
        return max(2, min(6, math.ceil(radius / 3)))

    def _apply_frame_style(self) -> None:
        self.configure(corner_radius=0, border_width=0, fg_color="transparent")

    def _apply_renderer_style(self) -> None:
        if not hasattr(self, "_renderer"):
            return
        self._renderer.configure_style(
            cell_padding_x=self._style_number("cell_padding_x"),
            badge_padding_x=self._style_number("badge_padding_x"),
            button_padding_x=self._style_number("button_padding_x"),
            badge_radius=self._style_number("badge_radius"),
            checkbox_radius=self._style_number("checkbox_radius"),
            progress_radius=self._style_number("progress_radius"),
            pill_radius=self._style_number("pill_radius"),
            action_radius=self._style_number("action_radius"),
        )

    def _style_number(self, key: str) -> float | None:
        value = getattr(self._table_style, key)
        if value is None:
            return None
        return max(0.0, float(value))

    def _theme_colors(self) -> dict[str, str]:
        signature = self._theme_colors_signature()
        if self._theme_colors_cache is not None and self._theme_colors_cache[0] == signature:
            return dict(self._theme_colors_cache[1])

        frame_bg = self._table_surface_color(self._theme_frame_color())
        outside_bg = self._surrounding_color(frame_bg)
        text = self._theme_color("CTkLabel", "text_color", ("#1f2933", "#f4f6fa"))
        button_bg = self._theme_color("CTkButton", "fg_color", ("#3b82f6", "#2563eb"))
        button_hover = self._theme_color("CTkButton", "hover_color", ("#2563eb", "#1d4ed8"))
        button_text = self._theme_color("CTkButton", "text_color", ("#ffffff", "#ffffff"))
        entry_border = self._theme_color("CTkEntry", "border_color", ("#c5cbd6", "#3d4350"))

        colors = {
            "canvas_bg": outside_bg,
            "surface_bg": self._blend(frame_bg, text, 0.02),
            "row_bg": self._blend(frame_bg, text, 0.02),
            "row_alt_bg": self._blend(frame_bg, text, 0.045),
            "header_bg": self._blend(frame_bg, text, 0.075),
            "footer_bg": self._blend(frame_bg, text, 0.065),
            "hover_bg": self._blend(frame_bg, button_bg, 0.12),
            "selected_bg": self._blend(frame_bg, button_bg, 0.28),
            "selected_hover_bg": self._blend(frame_bg, button_hover, 0.34),
            "text": text,
            "hover_text": text,
            "selected_text": text,
            "selected_hover_text": text,
            "muted_text": self._blend(frame_bg, text, 0.62),
            "header_text": text,
            "footer_text": text,
            "divider": self._blend(frame_bg, text, 0.13),
            "header_divider": self._blend(frame_bg, text, 0.10),
            "table_border": self._table_border_theme_color(self._blend(frame_bg, text, 0.16)),
            "sort_indicator": button_bg,
            "filter_indicator": button_bg,
            "badge_default_bg": self._blend(frame_bg, text, 0.18),
            "badge_text": text,
            "pill_bg": self._blend(frame_bg, button_bg, 0.14),
            "pill_text": text,
            "progress_bg": self._blend(frame_bg, text, 0.13),
            "progress_fill": button_bg,
            "progress_text": text,
            "link_text": button_bg,
            "checkbox_fill": frame_bg,
            "checkbox_fill_checked": button_bg,
            "checkbox_border": entry_border,
            "checkbox_check": button_text,
            "action_bg": self._blend(frame_bg, button_bg, 0.16),
            "action_border": self._blend(frame_bg, button_bg, 0.32),
            "action_text": text,
            "loading_indicator": button_bg,
        }
        for style_key, color_key in TABLE_STYLE_COLOR_MAP.items():
            value = getattr(self._table_style, style_key)
            if value is not None:
                colors[color_key] = self._resolve_color(value)
        self._theme_colors_cache = (signature, colors)
        return dict(colors)

    def _theme_colors_signature(self) -> tuple[str, ...]:
        return (
            ctk.get_appearance_mode().lower(),
            repr(self._table_fg_color),
            repr(self._table_border_color),
            repr(self._default_table_corner_radius),
            repr(self._default_table_border_width),
            repr(self._raw_surrounding_options()),
            repr(ctk.ThemeManager.theme.get("CTkFrame", {}).get("fg_color")),
            repr(ctk.ThemeManager.theme.get("CTkLabel", {}).get("text_color")),
            repr(ctk.ThemeManager.theme.get("CTkButton", {}).get("fg_color")),
            repr(ctk.ThemeManager.theme.get("CTkButton", {}).get("hover_color")),
            repr(ctk.ThemeManager.theme.get("CTkButton", {}).get("text_color")),
            repr(ctk.ThemeManager.theme.get("CTkEntry", {}).get("border_color")),
            repr(self._table_style),
        )

    def _raw_widget_option(self, option: str) -> Any:
        try:
            return self.cget(option)
        except Exception:
            return None

    def _raw_surrounding_options(self) -> tuple[str, ...]:
        values: list[str] = []
        parent = self.master
        while parent is not None:
            widget_values: list[str] = []
            for option in ("fg_color", "bg", "background"):
                try:
                    widget_values.append(repr(parent.cget(option)))
                except Exception:
                    continue
            if widget_values:
                values.extend(widget_values)
                break
            parent = getattr(parent, "master", None)
        return tuple(values)

    def _apply_action_colors(self, colors: dict[str, str]) -> None:
        for column in self._columns:
            for action in column.actions:
                if action.fg_color is not None:
                    colors[f"action_fill_{action.key}"] = self._resolve_color(action.fg_color)
                if action.text_color is not None:
                    colors[f"action_text_{action.key}"] = self._resolve_color(action.text_color)
                if action.border_color is not None:
                    colors[f"action_border_{action.key}"] = self._resolve_color(action.border_color)

    def _theme_color(self, widget: str, key: str, fallback: ColorValue) -> str:
        theme_value = ctk.ThemeManager.theme.get(widget, {}).get(key, fallback)
        return self._resolve_color(theme_value)

    def _widget_color(self, option: str, fallback: ColorValue) -> str:
        try:
            value = self.cget(option)
        except Exception:
            value = fallback
        if value is None or value == "transparent":
            value = fallback
        return self._resolve_color(value)

    def _table_surface_color(self, fallback: ColorValue) -> str:
        value = self._table_fg_color
        if value is None or value == "transparent":
            value = fallback
        return self._resolve_color(value)

    def _theme_frame_color(self) -> ColorValue:
        theme_value = ctk.ThemeManager.theme.get("CTkFrame", {}).get("fg_color")
        if theme_value is None:
            return ("#f7f8fb", "#2b2b2b")
        return cast(ColorValue, theme_value)

    def _table_border_theme_color(self, fallback: ColorValue) -> str:
        value = self._table_border_color
        if value is None or value == "transparent":
            value = fallback
        return self._resolve_color(value)

    def _surrounding_color(self, fallback: ColorValue) -> str:
        parent = self.master
        while parent is not None:
            for option in ("fg_color", "bg", "background"):
                try:
                    value = parent.cget(option)
                except Exception:
                    continue
                if value is None or value == "transparent":
                    continue
                return self._resolve_color(value)
            parent = getattr(parent, "master", None)
        return self._resolve_color(fallback)

    def _table_corner_radius(self) -> float:
        if self._table_style.corner_radius is not None:
            return max(0.0, float(self._table_style.corner_radius))
        return max(0.0, self._default_table_corner_radius)

    def _table_border_width(self) -> float:
        if self._table_style.border_width is not None:
            return max(0.0, float(self._table_style.border_width))
        return max(0.0, self._default_table_border_width)

    def _widget_number(self, option: str, fallback: float) -> float:
        try:
            value = self.cget(option)
        except Exception:
            return fallback
        if isinstance(value, (tuple, list)):
            value = value[0] if value else fallback
        try:
            return max(0.0, float(value))
        except (TypeError, ValueError):
            return fallback

    def _resolve_color(self, color: Any) -> str:
        try:
            apply_mode = self._apply_appearance_mode
            return str(apply_mode(color))
        except Exception:
            if isinstance(color, (tuple, list)):
                dark = ctk.get_appearance_mode().lower() == "dark"
                return str(color[1 if dark and len(color) > 1 else 0])
            return str(color)

    def _blend(self, base: str, overlay: str, amount: float) -> str:
        base_rgb = self._color_to_rgb(base)
        overlay_rgb = self._color_to_rgb(overlay)
        amount = min(1.0, max(0.0, amount))
        mixed = tuple(round(base_rgb[index] * (1 - amount) + overlay_rgb[index] * amount) for index in range(3))
        return f"#{mixed[0]:02x}{mixed[1]:02x}{mixed[2]:02x}"

    def _color_to_rgb(self, color: str) -> tuple[int, int, int]:
        try:
            red, green, blue = self.winfo_rgb(color)
            return (red // 256, green // 256, blue // 256)
        except tk.TclError:
            return (127, 127, 127)

    def _set_appearance_mode(self, mode_string: str) -> None:
        try:
            super()._set_appearance_mode(mode_string)
        finally:
            if hasattr(self, "_theme_colors_cache"):
                self._theme_colors_cache = None
            if hasattr(self, "_table_canvas"):
                self._redraw(full=True)
