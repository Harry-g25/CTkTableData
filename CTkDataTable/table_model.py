"""Non-visual data model for CTkDataTable."""

from __future__ import annotations

from bisect import bisect_left
from collections.abc import Callable, Iterable, Mapping, Sequence
from datetime import datetime
from typing import Any

from ._utils import normalize_row, normalize_rows, parse_datetime
from .table_column import TableColumn

RowData = dict[str, Any]
ColumnFilter = Mapping[str, Any] | Callable[[Any, RowData], bool]
CompiledColumnFilter = Callable[[RowData], bool]


class TableModel:
    """Own row data, sorting, filtering, and selection without tkinter state."""

    def __init__(self, columns: Sequence[TableColumn], data: Iterable[Any] = ()) -> None:
        self._columns = tuple(columns)
        self._source_data: list[RowData] = []
        self._view_indices: list[int] = []
        self._view_index_by_source: dict[int, int] = {}
        self._sort_state: tuple[str, bool] | None = None
        self._filter_query = ""
        self._column_filters: dict[str, ColumnFilter] = {}
        self._compiled_column_filters: dict[str, CompiledColumnFilter] = {}
        self._search_text_cache: dict[int, str] = {}
        self._selected_source_indices: set[int] = set()
        self._selection_anchor_source_index: int | None = None
        self.set_data(data)

    @property
    def source_data(self) -> list[RowData]:
        """Return the internal source rows for render-time reads."""

        return self._source_data

    @property
    def view_indices(self) -> list[int]:
        """Return source indices in their current filtered and sorted order."""

        return self._view_indices

    @property
    def sort_state(self) -> tuple[str, bool] | None:
        """Return the active sort key and direction."""

        return self._sort_state

    @property
    def filter_query(self) -> str:
        """Return the active filter query."""

        return self._filter_query

    @property
    def column_filters(self) -> dict[str, ColumnFilter]:
        """Return a shallow copy of active column filters."""

        return dict(self._column_filters)

    @property
    def selected_source_indices(self) -> frozenset[int]:
        """Return selected source-row indices."""

        return frozenset(self._selected_source_indices)

    @property
    def selection_anchor_source_index(self) -> int | None:
        """Return the source index used as the current range-selection anchor."""

        return self._selection_anchor_source_index

    def set_data(self, data: Iterable[Any]) -> None:
        """Replace all rows and clear selection."""

        self._source_data = normalize_rows(data)
        self._search_text_cache.clear()
        self.clear_selection()
        self._rebuild_view()

    def set_columns(
        self,
        columns: Sequence[TableColumn],
        *,
        rebuild: bool = True,
        clear_search_cache: bool = True,
    ) -> None:
        """Replace column definitions while preserving rows and compatible state."""

        self._columns = tuple(columns)
        column_keys = {column.key for column in self._columns}
        if self._sort_state is not None and self._sort_state[0] not in column_keys:
            self._sort_state = None
        self._column_filters = {
            column_key: definition
            for column_key, definition in self._column_filters.items()
            if column_key in column_keys
        }
        self._compiled_column_filters = {
            column_key: self._compile_column_filter(column_key, definition)
            for column_key, definition in self._column_filters.items()
        }
        if clear_search_cache:
            self._search_text_cache.clear()
        if rebuild:
            self._rebuild_view()
            self.prune_selection_to_view()

    def get_data(self) -> list[RowData]:
        """Return shallow copies of all source rows."""

        return [dict(row) for row in self._source_data]

    def get_visible_rows(self) -> list[RowData]:
        """Return shallow copies of rows in the current filtered and sorted view."""

        return [dict(self._source_data[index]) for index in self._view_indices]

    def clear(self) -> None:
        """Remove all rows."""

        self.set_data([])

    def sort_by(self, column_key: str, ascending: bool = True) -> None:
        """Sort visible rows by a column key."""

        self.require_column(column_key)
        self._sort_state = (column_key, bool(ascending))
        self._rebuild_view()

    def search(self, query: str) -> set[int]:
        """Filter rows across visible, non-action columns and return selection changes."""

        self._filter_query = str(query)
        self._rebuild_view()
        return self.prune_selection_to_view()

    def set_column_filter(self, column_key: str, definition: ColumnFilter) -> set[int]:
        """Set a filter for one column and return changed selection indices."""

        self.require_column(column_key)
        if not callable(definition) and not isinstance(definition, Mapping):
            raise TypeError("Column filter definitions must be mappings or callables.")
        compiled_filter = self._compile_column_filter(column_key, definition)
        self._column_filters[column_key] = definition
        self._compiled_column_filters[column_key] = compiled_filter
        self._rebuild_view()
        return self.prune_selection_to_view()

    def clear_column_filter(self, column_key: str) -> set[int]:
        """Clear one column filter and return changed selection indices."""

        self.require_column(column_key)
        self._column_filters.pop(column_key, None)
        self._compiled_column_filters.pop(column_key, None)
        self._rebuild_view()
        return self.prune_selection_to_view()

    def clear_column_filters(self) -> set[int]:
        """Clear all column filters and return changed selection indices."""

        self._column_filters.clear()
        self._compiled_column_filters.clear()
        self._rebuild_view()
        return self.prune_selection_to_view()

    def filter(self, query: str) -> set[int]:
        """Alias for :meth:`search`."""

        return self.search(query)

    def add_row(self, row: Any) -> int:
        """Append one row and return its source index."""

        self._source_data.append(normalize_row(row))
        self._rebuild_view()
        return len(self._source_data) - 1

    def add_rows(self, rows: Iterable[Any]) -> list[int]:
        """Append multiple rows in a single rebuild and return their source indices."""

        start = len(self._source_data)
        self._source_data.extend(normalize_row(row) for row in rows)
        self._rebuild_view()
        return list(range(start, len(self._source_data)))

    def update_row(self, index: int, row: Any) -> None:
        """Replace a source row."""

        self.validate_source_index(index)
        self._source_data[index] = normalize_row(row)
        self._search_text_cache.pop(index, None)
        self._rebuild_view()
        self._drop_invalid_selection()

    def delete_row(self, index: int) -> None:
        """Delete a row by source-data index and shift selection."""

        self.validate_source_index(index)
        del self._source_data[index]

        shifted_selection: set[int] = set()
        for selected_index in self._selected_source_indices:
            if selected_index == index:
                continue
            shifted_selection.add(selected_index - 1 if selected_index > index else selected_index)
        self._selected_source_indices = shifted_selection

        if self._selection_anchor_source_index == index:
            self._selection_anchor_source_index = None
        elif self._selection_anchor_source_index is not None and self._selection_anchor_source_index > index:
            self._selection_anchor_source_index -= 1

        self._search_text_cache.clear()
        self._rebuild_view()
        self._drop_invalid_selection()

    def delete_rows(self, indices: Iterable[int]) -> int:
        """Delete multiple source rows in a single rebuild and return the number removed."""

        unique_indices = sorted(set(indices))
        if not unique_indices:
            return 0
        for index in unique_indices:
            self.validate_source_index(index)
        indices_set = set(unique_indices)

        for index in reversed(unique_indices):
            del self._source_data[index]

        self._search_text_cache.clear()
        new_selection: set[int] = set()
        for si in self._selected_source_indices:
            if si in indices_set:
                continue
            shift = bisect_left(unique_indices, si)
            new_selection.add(si - shift)
        self._selected_source_indices = new_selection

        if self._selection_anchor_source_index in indices_set:
            self._selection_anchor_source_index = None
        elif self._selection_anchor_source_index is not None:
            shift = bisect_left(unique_indices, self._selection_anchor_source_index)
            self._selection_anchor_source_index -= shift

        self._rebuild_view()
        self._drop_invalid_selection()
        return len(unique_indices)

    def delete_row_by_key(self, column_key: str, value: Any) -> bool:
        """Delete the first row whose column value matches value."""

        index = self.find_source_index(column_key, value)
        if index is None:
            return False
        self.delete_row(index)
        return True

    def delete_row_where(self, column_key: str, value: Any) -> bool:
        """Alias for :meth:`delete_row_by_key`."""

        return self.delete_row_by_key(column_key, value)

    def update_row_where(self, column_key: str, value: Any, new_row: Any) -> bool:
        """Update the first row whose column matches value.  Returns True if found."""

        index = self.find_source_index(column_key, value)
        if index is None:
            return False
        self.update_row(index, new_row)
        return True

    def find_source_index(self, column_key: str, value: Any) -> int | None:
        """Return the first source index whose column value matches value."""

        self.require_column(column_key)
        for index, row in enumerate(self._source_data):
            if row.get(column_key) == value:
                return index
        return None

    def get_row(self, source_index: int) -> RowData:
        """Return a shallow copy of one source row."""

        self.validate_source_index(source_index)
        return dict(self._source_data[source_index])

    def row_for_view_index(self, view_index: int) -> RowData:
        """Return the internal row for a view index."""

        self.validate_view_index(view_index)
        return self._source_data[self._view_indices[view_index]]

    def source_index_for_view_index(self, view_index: int) -> int:
        """Return source index for a view index."""

        self.validate_view_index(view_index)
        return self._view_indices[view_index]

    def view_index_for_source_index(self, source_index: int) -> int | None:
        """Return visible view index for a source index, if present."""

        try:
            return self._view_index_by_source[source_index]
        except KeyError:
            return None

    def get_selected_rows(self, *, visible_only: bool = False) -> list[RowData]:
        """Return selected rows as shallow copies."""

        return [dict(self._source_data[index]) for index in self.get_selected_source_indices(visible_only=visible_only)]

    def get_selected_source_indices(self, *, visible_only: bool = False) -> list[int]:
        """Return selected source indices in current view order."""

        ordered_indices = [index for index in self._view_indices if index in self._selected_source_indices]
        if visible_only:
            return ordered_indices
        hidden_selected = sorted(self._selected_source_indices.difference(ordered_indices))
        return [index for index in ordered_indices + hidden_selected if 0 <= index < len(self._source_data)]

    def get_selected_view_indices(self) -> list[int]:
        """Return selected rows as current view indices."""

        return [
            view_index
            for view_index, source_index in enumerate(self._view_indices)
            if source_index in self._selected_source_indices
        ]

    def clear_selection(self) -> None:
        """Clear selected rows and range anchor."""

        self._selected_source_indices.clear()
        self._selection_anchor_source_index = None

    def prune_selection_to_view(self) -> set[int]:
        """Remove selections that are no longer visible and return changed indices."""

        old_selection = set(self._selected_source_indices)
        visible = set(self._view_indices)
        self._selected_source_indices.intersection_update(visible)
        if self._selection_anchor_source_index not in self._selected_source_indices:
            self._selection_anchor_source_index = None
        return old_selection.symmetric_difference(self._selected_source_indices)

    def select_view_index(
        self,
        view_index: int,
        *,
        multi_select: bool = False,
        shift: bool = False,
        control: bool = False,
    ) -> set[int]:
        """Select a visible row and return changed source indices."""

        self.validate_view_index(view_index)
        source_index = self._view_indices[view_index]
        old_selection = set(self._selected_source_indices)
        anchor_view_index = (
            self._view_index_by_source.get(self._selection_anchor_source_index)
            if self._selection_anchor_source_index is not None
            else None
        )

        if multi_select and shift and anchor_view_index is not None:
            start = min(anchor_view_index, view_index)
            end = max(anchor_view_index, view_index)
            self._selected_source_indices = set(self._view_indices[start : end + 1])
        elif multi_select and control:
            if source_index in self._selected_source_indices:
                self._selected_source_indices.remove(source_index)
            else:
                self._selected_source_indices.add(source_index)
            self._selection_anchor_source_index = source_index
        else:
            self._selected_source_indices = {source_index}
            self._selection_anchor_source_index = source_index

        return old_selection.symmetric_difference(self._selected_source_indices)

    def focused_view_index(self) -> int | None:
        """Return the best current view index for keyboard navigation."""

        if self._selection_anchor_source_index is not None:
            view_index = self.view_index_for_source_index(self._selection_anchor_source_index)
            if view_index is not None:
                return view_index

        selected = self.get_selected_source_indices(visible_only=True)
        if selected:
            return self.view_index_for_source_index(selected[0])

        return None

    def visible_columns(self) -> list[TableColumn]:
        """Return columns currently included in the view."""

        return [column for column in self._columns if column.visible]

    def require_column(self, column_key: str) -> TableColumn:
        """Return a column or raise a clear error."""

        for column in self._columns:
            if column.key == column_key:
                return column
        raise KeyError(f"Unknown column key '{column_key}'.")

    def validate_source_index(self, index: int) -> None:
        """Raise when source index is outside the data list."""

        if index < 0 or index >= len(self._source_data):
            raise IndexError(f"Row index {index} is out of range.")

    def validate_view_index(self, index: int) -> None:
        """Raise when view index is outside the current filtered view."""

        if index < 0 or index >= len(self._view_indices):
            raise IndexError(f"View row index {index} is out of range.")

    def _rebuild_view(self) -> None:
        search_query = self._filter_query.strip().casefold()
        if search_query or self._compiled_column_filters:
            self._view_indices = [
                index
                for index, row in enumerate(self._source_data)
                if self._row_matches_search(index, row, search_query) and self._row_matches_column_filters(row)
            ]
        else:
            self._view_indices = list(range(len(self._source_data)))

        if self._sort_state is not None:
            column_key, ascending = self._sort_state
            self._view_indices = self._sorted_indices(self._view_indices, column_key, ascending)

        self._view_index_by_source = {
            source_index: view_index for view_index, source_index in enumerate(self._view_indices)
        }

    def _row_matches_search(self, source_index: int, row: RowData, normalized_query: str) -> bool:
        if not normalized_query:
            return True
        text = self._search_text_cache.get(source_index)
        if text is None:
            text = self._search_text(row)
            self._search_text_cache[source_index] = text
        return normalized_query in text

    def _search_text(self, row: RowData) -> str:
        values: list[str] = []
        for column in self.visible_columns():
            if column.type == "action":
                continue
            value = row.get(column.key)
            if value is not None:
                values.append(str(value).casefold())
        return "\n".join(values)

    def _row_matches_column_filters(self, row: RowData) -> bool:
        for column_key, predicate in self._compiled_column_filters.items():
            try:
                if not predicate(row):
                    return False
            except Exception as error:
                raise RuntimeError(f"Column filter for '{column_key}' failed: {error}") from error
        return True

    def _compile_column_filter(self, column_key: str, definition: ColumnFilter) -> CompiledColumnFilter:
        if callable(definition):
            def callable_filter(row: RowData) -> bool:
                return bool(definition(row.get(column_key), row))

            return callable_filter

        filter_type = str(definition.get("type", "contains")).casefold()
        if filter_type == "contains":
            needle = str(definition.get("value", "")).casefold()

            def contains_filter(row: RowData) -> bool:
                return needle in str(row.get(column_key) or "").casefold()

            return contains_filter
        if filter_type == "equals":
            expected = definition.get("value")

            def equals_filter(row: RowData) -> bool:
                return row.get(column_key) == expected

            return equals_filter
        if filter_type == "not_equals":
            expected = definition.get("value")

            def not_equals_filter(row: RowData) -> bool:
                return row.get(column_key) != expected

            return not_equals_filter
        if filter_type == "in":
            values = definition.get("values", ())
            if isinstance(values, str):
                raise TypeError(f"Column filter for '{column_key}' type 'in' requires a non-string iterable 'values'.")
            try:
                value_set = set(values)
            except TypeError as error:
                raise TypeError(f"Column filter for '{column_key}' type 'in' requires an iterable 'values'.") from error

            def in_filter(row: RowData) -> bool:
                return row.get(column_key) in value_set

            return in_filter
        if filter_type == "bool":
            expected = bool(definition.get("value"))

            def bool_filter(row: RowData) -> bool:
                return bool(row.get(column_key)) is expected

            return bool_filter
        if filter_type == "range":
            min_number = self._optional_float_bound(definition.get("min"), column_key, "min")
            max_number = self._optional_float_bound(definition.get("max"), column_key, "max")

            def range_filter(row: RowData) -> bool:
                return self._value_in_number_range(row.get(column_key), min_number, max_number)

            return range_filter
        if filter_type == "date_range":
            min_date = self._optional_datetime_bound(definition.get("min"), column_key, "min")
            max_date = self._optional_datetime_bound(definition.get("max"), column_key, "max")

            def date_range_filter(row: RowData) -> bool:
                return self._value_in_date_range(row.get(column_key), min_date, max_date)

            return date_range_filter
        raise ValueError(f"Column filter type '{filter_type}' is not supported.")

    def _optional_float_bound(self, value: Any, column_key: str, bound_name: str) -> float | None:
        if value is None:
            return None
        try:
            return float(str(value).replace(",", ""))
        except (TypeError, ValueError) as error:
            message = f"Column filter for '{column_key}' has invalid {bound_name} range value {value!r}."
            raise ValueError(message) from error

    def _optional_datetime_bound(self, value: Any, column_key: str, bound_name: str) -> datetime | None:
        if value is None:
            return None
        parsed = parse_datetime(value)
        if parsed is None:
            raise ValueError(f"Column filter for '{column_key}' has invalid {bound_name} date value {value!r}.")
        return parsed

    def _value_in_number_range(self, value: Any, minimum: float | None, maximum: float | None) -> bool:
        try:
            number = float(str(value).replace(",", ""))
        except (TypeError, ValueError):
            return False
        if minimum is not None and number < minimum:
            return False
        return not (maximum is not None and number > maximum)

    def _value_in_date_range(self, value: Any, minimum: datetime | None, maximum: datetime | None) -> bool:
        parsed = parse_datetime(value)
        if parsed is None:
            return False
        if minimum is not None and parsed < minimum:
            return False
        return not (maximum is not None and parsed > maximum)

    def _sorted_indices(self, indices: list[int], column_key: str, ascending: bool) -> list[int]:
        column = self.require_column(column_key)
        decorated = [(self._sort_value(self._source_data[index].get(column_key), column), index) for index in indices]
        sortable = [(sort_key, index) for sort_key, index in decorated if sort_key is not None]
        missing = [index for sort_key, index in decorated if sort_key is None]

        sortable.sort(key=lambda item: item[0], reverse=not ascending)
        return [index for _sort_key, index in sortable] + missing

    def _sort_value(self, value: Any, column: TableColumn) -> tuple[int, Any] | None:
        if value is None or value == "":
            return None
        if column.type in {"number", "percentage", "currency", "progress"}:
            try:
                return (0, float(str(value).replace(",", "")))
            except (TypeError, ValueError):
                return None
        if column.type in {"date", "datetime"}:
            parsed = parse_datetime(value)
            if parsed is not None:
                return (0, parsed.timestamp())
            return None
        if column.type == "checkbox":
            return (0, bool(value))
        return (0, str(value).casefold())

    def _drop_invalid_selection(self) -> None:
        valid_indices = set(range(len(self._source_data)))
        self._selected_source_indices.intersection_update(valid_indices)
        if self._selection_anchor_source_index not in self._selected_source_indices:
            self._selection_anchor_source_index = None
