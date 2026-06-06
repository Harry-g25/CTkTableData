"""Column definitions for the CTkDataTable widget."""

from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any, Literal, TypeAlias, cast

ColumnAlign = Literal["left", "center", "right"]
ColumnType = Literal[
    "text",
    "number",
    "percentage",
    "currency",
    "date",
    "datetime",
    "badge",
    "checkbox",
    "action",
    "progress",
    "link",
    "pill_list",
]
ColorValue = str | tuple[str, str]


@dataclass(frozen=True)
class BadgeStyle:
    """Resolved display information for a badge cell."""

    text: str
    fill_color: ColorValue
    text_color: ColorValue | None = None


BadgeFallbackResult = BadgeStyle | ColorValue | None
BadgeFallbackHandler = Callable[[Any, Mapping[str, Any], "TableColumn"], BadgeFallbackResult]
CellFormatter = Callable[[Any, Mapping[str, Any]], str]
NumberFormatter = str | Callable[[Any], str]


@dataclass(frozen=True)
class TableAction:
    """Definition for a Canvas-rendered action button inside an action cell."""

    key: str
    label: str
    width: int | None = None
    fg_color: ColorValue | None = None
    text_color: ColorValue | None = None
    border_color: ColorValue | None = None

    @classmethod
    def from_definition(cls, definition: TableAction | Mapping[str, Any] | str) -> TableAction:
        """Create a table action from an existing action or mapping definition."""

        if isinstance(definition, cls):
            return definition
        if isinstance(definition, str):
            return cls(key=definition, label=definition.title())
        if not isinstance(definition, Mapping):
            raise TypeError("Action definitions must be TableAction objects, mappings, or strings.")
        if "key" not in definition:
            raise ValueError("Action definitions require a 'key'.")

        key = str(definition["key"])
        label = str(definition.get("label", key.title()))
        width_value = definition.get("width")
        width = int(width_value) if width_value is not None else None
        if width is not None and width <= 0:
            raise ValueError(f"Action '{key}' width must be greater than zero.")

        return cls(
            key=key,
            label=label,
            width=width,
            fg_color=definition.get("fg_color"),
            text_color=definition.get("text_color"),
            border_color=definition.get("border_color"),
        )


@dataclass(frozen=True)
class TableColumn:
    """Typed configuration for a CTkDataTable column."""

    key: str
    title: str
    width: int
    align: ColumnAlign = "left"
    visible: bool = True
    sortable: bool = True
    type: ColumnType = "text"
    badge_colors: Mapping[str, ColorValue] = field(default_factory=dict)
    badge_fallback_color: ColorValue | None = None
    badge_fallback_handler: BadgeFallbackHandler | None = None
    pill_colors: Mapping[str, ColorValue] = field(default_factory=dict)
    pill_fallback_color: ColorValue | None = None
    pill_text_color: ColorValue | None = None
    actions: tuple[TableAction, ...] = ()
    formatter: CellFormatter | None = None
    number_format: NumberFormatter | None = None
    percentage_format: str = "{value:.0f}%"
    percentage_multiplier: float = 1.0
    currency_symbol: str = "$"
    currency_format: str = "{symbol}{value:,.2f}"
    currency_negative_format: str = "-{symbol}{value:,.2f}"
    date_format: str = "%Y-%m-%d"
    datetime_format: str = "%Y-%m-%d %H:%M"
    progress_min: float = 0.0
    progress_max: float = 100.0
    progress_color: ColorValue | None = None
    progress_background_color: ColorValue | None = None
    progress_show_text: bool = True
    progress_text_format: str = "{percent:.0f}%"
    link_color: ColorValue | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)

    @classmethod
    def from_definition(cls, definition: TableColumn | Mapping[str, Any]) -> TableColumn:
        """Create a column from an existing TableColumn or a dictionary definition."""

        if isinstance(definition, cls):
            return definition
        if not isinstance(definition, Mapping):
            raise TypeError("Column definitions must be TableColumn objects or mappings.")
        if "key" not in definition:
            raise ValueError("Column definitions require a 'key'.")

        column_type = _validate_type(str(definition.get("type", "text")))
        align = _validate_align(str(definition.get("align", _default_align(column_type))))
        key = str(definition["key"])
        width = int(definition.get("width", 140))
        if width <= 0:
            raise ValueError(f"Column '{key}' width must be greater than zero.")

        raw_actions = definition.get("actions", ())
        actions = tuple(TableAction.from_definition(action) for action in _as_sequence(raw_actions))

        badge_colors = definition.get("badge_colors", {})
        if not isinstance(badge_colors, Mapping):
            raise TypeError(f"Column '{key}' badge_colors must be a mapping.")
        pill_colors = definition.get("pill_colors", {})
        if not isinstance(pill_colors, Mapping):
            raise TypeError(f"Column '{key}' pill_colors must be a mapping.")
        fallback_color = definition.get("badge_fallback_color")
        fallback_handler = definition.get("badge_fallback_handler")
        if fallback_handler is not None and not callable(fallback_handler):
            raise TypeError(f"Column '{key}' badge fallback handler must be callable.")
        formatter = definition.get("formatter")
        if formatter is not None and not callable(formatter):
            raise TypeError(f"Column '{key}' formatter must be callable.")
        number_format = definition.get("number_format")
        if number_format is not None and not isinstance(number_format, str) and not callable(number_format):
            raise TypeError(f"Column '{key}' number_format must be a format string or callable.")
        percentage_multiplier = float(definition.get("percentage_multiplier", 1.0))
        if percentage_multiplier <= 0:
            raise ValueError(f"Column '{key}' percentage_multiplier must be greater than zero.")
        progress_min = float(definition.get("progress_min", 0.0))
        progress_max = float(definition.get("progress_max", 100.0))
        if progress_max <= progress_min:
            raise ValueError(f"Column '{key}' progress_max must be greater than progress_min.")
        metadata = definition.get("metadata", {})
        if not isinstance(metadata, Mapping):
            raise TypeError(f"Column '{key}' metadata must be a mapping.")

        return cls(
            key=key,
            title=str(definition.get("title", key.replace("_", " ").title())),
            width=width,
            align=align,
            visible=bool(definition.get("visible", True)),
            sortable=bool(definition.get("sortable", True)),
            type=column_type,
            badge_colors={str(value): color for value, color in dict(badge_colors).items()},
            badge_fallback_color=fallback_color,
            badge_fallback_handler=fallback_handler,
            pill_colors={str(value): color for value, color in dict(pill_colors).items()},
            pill_fallback_color=definition.get("pill_fallback_color"),
            pill_text_color=definition.get("pill_text_color"),
            actions=actions,
            formatter=formatter,
            number_format=number_format,
            percentage_format=str(definition.get("percentage_format", "{value:.0f}%")),
            percentage_multiplier=percentage_multiplier,
            currency_symbol=str(definition.get("currency_symbol", "$")),
            currency_format=str(definition.get("currency_format", "{symbol}{value:,.2f}")),
            currency_negative_format=str(definition.get("currency_negative_format", "-{symbol}{value:,.2f}")),
            date_format=str(definition.get("date_format", "%Y-%m-%d")),
            datetime_format=str(definition.get("datetime_format", "%Y-%m-%d %H:%M")),
            progress_min=progress_min,
            progress_max=progress_max,
            progress_color=definition.get("progress_color"),
            progress_background_color=definition.get("progress_background_color"),
            progress_show_text=bool(definition.get("progress_show_text", True)),
            progress_text_format=str(definition.get("progress_text_format", "{percent:.0f}%")),
            link_color=definition.get("link_color"),
            metadata=dict(metadata),
        )


class Column(Mapping):
    """Fluent builder for a :class:`TableColumn`.

    Usage::

        Column("status").title("Status").width(130).badge(
            colors={"Open": "#2ecc71", "Closed": "#e74c3c"},
            fallback_color="#64748b",
        )
        Column("amount").title("Amount").width(120).number(format="${:,.2f}")
        Column("actions").title("Actions").width(170).action(
            buttons=[{"key": "view", "label": "View"}, {"key": "edit", "label": "Edit"}],
        )
    """

    def __init__(self, key: str) -> None:
        self._data: dict[str, Any] = {"key": key, "type": "text"}

    def __getitem__(self, key: str) -> Any:
        return self._data[key]

    def __iter__(self) -> Any:
        return iter(self._data)

    def __len__(self) -> int:
        return len(self._data)

    def title(self, title: str) -> Column:
        """Set the column header label."""
        self._data["title"] = title
        return self

    def width(self, pixels: int) -> Column:
        """Set the column width in pixels."""
        self._data["width"] = pixels
        return self

    def align(self, align: ColumnAlign) -> Column:
        """Set text alignment: 'left', 'center', or 'right'."""
        self._data["align"] = align
        return self

    def hide(self) -> Column:
        """Mark this column as hidden."""
        self._data["visible"] = False
        return self

    def no_sort(self) -> Column:
        """Disable sorting for this column."""
        self._data["sortable"] = False
        return self

    def fmt(self, func: CellFormatter) -> Column:
        """Set a cell formatter callable ``(value, row) -> str``."""
        self._data["formatter"] = func
        return self

    def metadata(self, **kwargs: Any) -> Column:
        """Attach arbitrary metadata to this column."""
        self._data["metadata"] = kwargs
        return self

    def text(self) -> Column:
        """Plain text column (default)."""
        self._data["type"] = "text"
        return self

    def number(self, format: NumberFormatter | None = None) -> Column:
        """Numeric column with optional format string or callable."""
        self._data["type"] = "number"
        if format is not None:
            self._data["number_format"] = format
        return self

    def percentage(self, *, format: str = "{value:.0f}%", multiplier: float = 1.0) -> Column:
        """Percentage column with configurable display formatting."""
        self._data["type"] = "percentage"
        self._data["percentage_format"] = format
        self._data["percentage_multiplier"] = multiplier
        return self

    def currency(
        self,
        *,
        symbol: str = "$",
        format: str = "{symbol}{value:,.2f}",
        negative_format: str = "-{symbol}{value:,.2f}",
    ) -> Column:
        """Currency column with configurable positive and negative formatting."""
        self._data["type"] = "currency"
        self._data["currency_symbol"] = symbol
        self._data["currency_format"] = format
        self._data["currency_negative_format"] = negative_format
        return self

    def date(self, fmt: str = "%Y-%m-%d") -> Column:
        """Date column with optional strftime format."""
        self._data["type"] = "date"
        self._data["date_format"] = fmt
        return self

    def datetime(self, fmt: str = "%Y-%m-%d %H:%M") -> Column:
        """Datetime column with optional strftime format."""
        self._data["type"] = "datetime"
        self._data["datetime_format"] = fmt
        return self

    def badge(
        self,
        colors: Mapping[str, ColorValue] | None = None,
        fallback_color: ColorValue | None = None,
        fallback_handler: BadgeFallbackHandler | None = None,
    ) -> Column:
        """Badge column mapping values to colours."""
        self._data["type"] = "badge"
        if colors is not None:
            self._data["badge_colors"] = dict(colors)
        if fallback_color is not None:
            self._data["badge_fallback_color"] = fallback_color
        if fallback_handler is not None:
            self._data["badge_fallback_handler"] = fallback_handler
        return self

    def pill_list(
        self,
        colors: Mapping[str, ColorValue] | None = None,
        fallback_color: ColorValue | None = None,
        text_color: ColorValue | None = None,
    ) -> Column:
        """Pill-list column for compact tag displays."""
        self._data["type"] = "pill_list"
        if colors is not None:
            self._data["pill_colors"] = dict(colors)
        if fallback_color is not None:
            self._data["pill_fallback_color"] = fallback_color
        if text_color is not None:
            self._data["pill_text_color"] = text_color
        return self

    def checkbox(self) -> Column:
        """Boolean checkbox column."""
        self._data["type"] = "checkbox"
        return self

    def progress(
        self,
        *,
        minimum: float = 0.0,
        maximum: float = 100.0,
        color: ColorValue | None = None,
        background_color: ColorValue | None = None,
        show_text: bool = True,
        text_format: str = "{percent:.0f}%",
    ) -> Column:
        """Progress-bar column for numeric completion values."""
        self._data["type"] = "progress"
        self._data["progress_min"] = minimum
        self._data["progress_max"] = maximum
        self._data["progress_show_text"] = show_text
        self._data["progress_text_format"] = text_format
        if color is not None:
            self._data["progress_color"] = color
        if background_color is not None:
            self._data["progress_background_color"] = background_color
        return self

    def link(self, color: ColorValue | None = None) -> Column:
        """Link-style clickable text column."""
        self._data["type"] = "link"
        if color is not None:
            self._data["link_color"] = color
        return self

    def action(
        self,
        buttons: Sequence[Any],
        *,
        sortable: bool = False,
    ) -> Column:
        """Action-button column.  Pass a list of button definitions."""
        self._data["type"] = "action"
        self._data["actions"] = buttons
        self._data["sortable"] = sortable
        return self


ColumnDefinition: TypeAlias = TableColumn | Column | Mapping[str, Any]


def normalize_columns(columns: Sequence[ColumnDefinition]) -> tuple[TableColumn, ...]:
    """Normalize a sequence of user supplied column definitions."""

    normalized = tuple(TableColumn.from_definition(column) for column in columns)
    seen: set[str] = set()
    for column in normalized:
        if column.key in seen:
            raise ValueError(f"Duplicate column key '{column.key}'.")
        seen.add(column.key)
    return normalized


def _as_sequence(value: Any) -> Iterable[Any]:
    if value is None:
        return ()
    if isinstance(value, Mapping):
        return (value,)
    if isinstance(value, str):
        return ({"key": value, "label": value.title()},)
    if not isinstance(value, Iterable):
        raise TypeError("Action definitions must be an action mapping, string, or iterable of actions.")
    return value


def _default_align(column_type: ColumnType) -> ColumnAlign:
    if column_type in {"number", "percentage", "currency"}:
        return "right"
    if column_type in {"checkbox", "action", "progress"}:
        return "center"
    return "left"


def _validate_align(value: str) -> ColumnAlign:
    if value not in {"left", "center", "right"}:
        raise ValueError("Column align must be 'left', 'center', or 'right'.")
    return cast(ColumnAlign, value)


def _validate_type(value: str) -> ColumnType:
    valid_types = {
        "text",
        "number",
        "percentage",
        "currency",
        "date",
        "datetime",
        "badge",
        "checkbox",
        "action",
        "progress",
        "link",
        "pill_list",
    }
    if value not in valid_types:
        raise ValueError(f"Column type '{value}' is not supported.")
    return cast(ColumnType, value)
