"""Table-wide styling options for CTkDataTable."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, fields, replace
from typing import Any, TypeAlias

from .table_column import ColorValue


@dataclass(frozen=True)
class TableStyle:
    """Optional colors, spacing, and radii for a CTkDataTable.

    Any field left as None falls back to the active CustomTkinter theme.
    """

    corner_radius: float | None = None
    border_width: float | None = None
    cell_padding_x: int | None = None
    badge_padding_x: int | None = None
    button_padding_x: int | None = None
    badge_radius: float | None = None
    checkbox_radius: float | None = None
    progress_radius: float | None = None
    pill_radius: float | None = None
    action_radius: float | None = None

    canvas_bg: ColorValue | None = None
    surface_bg: ColorValue | None = None
    row_bg: ColorValue | None = None
    row_alt_bg: ColorValue | None = None
    header_bg: ColorValue | None = None
    footer_bg: ColorValue | None = None
    hover_bg: ColorValue | None = None
    selected_bg: ColorValue | None = None
    selected_hover_bg: ColorValue | None = None
    text_color: ColorValue | None = None
    hover_text_color: ColorValue | None = None
    selected_text_color: ColorValue | None = None
    selected_hover_text_color: ColorValue | None = None
    muted_text_color: ColorValue | None = None
    header_text_color: ColorValue | None = None
    footer_text_color: ColorValue | None = None
    divider_color: ColorValue | None = None
    header_divider_color: ColorValue | None = None
    border_color: ColorValue | None = None
    sort_indicator_color: ColorValue | None = None
    filter_indicator_color: ColorValue | None = None
    badge_bg: ColorValue | None = None
    badge_text_color: ColorValue | None = None
    pill_bg: ColorValue | None = None
    pill_text_color: ColorValue | None = None
    progress_bg: ColorValue | None = None
    progress_fill: ColorValue | None = None
    progress_text_color: ColorValue | None = None
    link_text_color: ColorValue | None = None
    checkbox_fill: ColorValue | None = None
    checkbox_fill_checked: ColorValue | None = None
    checkbox_border: ColorValue | None = None
    checkbox_check: ColorValue | None = None
    action_bg: ColorValue | None = None
    action_border: ColorValue | None = None
    action_text_color: ColorValue | None = None
    loading_indicator_color: ColorValue | None = None


TableStyleDefinition: TypeAlias = TableStyle | Mapping[str, Any]

TABLE_STYLE_COLOR_MAP = {
    "canvas_bg": "canvas_bg",
    "surface_bg": "surface_bg",
    "row_bg": "row_bg",
    "row_alt_bg": "row_alt_bg",
    "header_bg": "header_bg",
    "footer_bg": "footer_bg",
    "hover_bg": "hover_bg",
    "selected_bg": "selected_bg",
    "selected_hover_bg": "selected_hover_bg",
    "text_color": "text",
    "hover_text_color": "hover_text",
    "selected_text_color": "selected_text",
    "selected_hover_text_color": "selected_hover_text",
    "muted_text_color": "muted_text",
    "header_text_color": "header_text",
    "footer_text_color": "footer_text",
    "divider_color": "divider",
    "header_divider_color": "header_divider",
    "border_color": "table_border",
    "sort_indicator_color": "sort_indicator",
    "filter_indicator_color": "filter_indicator",
    "badge_bg": "badge_default_bg",
    "badge_text_color": "badge_text",
    "pill_bg": "pill_bg",
    "pill_text_color": "pill_text",
    "progress_bg": "progress_bg",
    "progress_fill": "progress_fill",
    "progress_text_color": "progress_text",
    "link_text_color": "link_text",
    "checkbox_fill": "checkbox_fill",
    "checkbox_fill_checked": "checkbox_fill_checked",
    "checkbox_border": "checkbox_border",
    "checkbox_check": "checkbox_check",
    "action_bg": "action_bg",
    "action_border": "action_border",
    "action_text_color": "action_text",
    "loading_indicator_color": "loading_indicator",
}

TABLE_STYLE_DIMENSION_FIELDS = {
    "corner_radius",
    "border_width",
    "cell_padding_x",
    "badge_padding_x",
    "button_padding_x",
    "badge_radius",
    "checkbox_radius",
    "progress_radius",
    "pill_radius",
    "action_radius",
}

_FIELD_NAMES = {field.name for field in fields(TableStyle)}
_ALIASES = {
    "fg_color": "canvas_bg",
    "text": "text_color",
    "hover_text": "hover_text_color",
    "selected_text": "selected_text_color",
    "selected_hover_text": "selected_hover_text_color",
    "muted_text": "muted_text_color",
    "header_text": "header_text_color",
    "footer_text": "footer_text_color",
    "divider": "divider_color",
    "header_divider": "header_divider_color",
    "table_border": "border_color",
    "sort_indicator": "sort_indicator_color",
    "filter_indicator": "filter_indicator_color",
    "badge_default_bg": "badge_bg",
    "badge_text": "badge_text_color",
    "pill_text": "pill_text_color",
    "progress_text": "progress_text_color",
    "link_text": "link_text_color",
    "action_text": "action_text_color",
    "loading_indicator": "loading_indicator_color",
}


def normalize_table_style(style: TableStyleDefinition | None = None, **overrides: Any) -> TableStyle:
    """Return a TableStyle from a TableStyle, mapping, or keyword overrides."""

    values: dict[str, Any] = {}
    if style is not None:
        if isinstance(style, TableStyle):
            values.update(_style_values(style, include_none=False))
        elif isinstance(style, Mapping):
            values.update(_normalize_style_mapping(style))
        else:
            raise TypeError("style must be a TableStyle, mapping, or None.")
    if overrides:
        values.update(_normalize_style_mapping(overrides))
    _validate_dimensions(values)
    return TableStyle(**values)


def merge_table_style(base: TableStyle, style: TableStyleDefinition | None = None, **overrides: Any) -> TableStyle:
    """Merge style options onto an existing TableStyle."""

    values = _style_values(base, include_none=False)
    if style is not None:
        if isinstance(style, TableStyle):
            values.update(_style_values(style, include_none=False))
        elif isinstance(style, Mapping):
            values.update(_normalize_style_mapping(style))
        else:
            raise TypeError("style must be a TableStyle, mapping, or None.")
    if overrides:
        values.update(_normalize_style_mapping(overrides))
    _validate_dimensions(values)
    return replace(base, **values)


def _style_values(style: TableStyle, *, include_none: bool) -> dict[str, Any]:
    values = {field.name: getattr(style, field.name) for field in fields(TableStyle)}
    if include_none:
        return values
    return {key: value for key, value in values.items() if value is not None}


def _normalize_style_mapping(style: Mapping[str, Any]) -> dict[str, Any]:
    values: dict[str, Any] = {}
    for raw_key, value in style.items():
        key = _ALIASES.get(str(raw_key), str(raw_key))
        if key not in _FIELD_NAMES:
            raise ValueError(f"Unknown table style option '{raw_key}'.")
        values[key] = value
    return values


def _validate_dimensions(values: Mapping[str, Any]) -> None:
    for key in TABLE_STYLE_DIMENSION_FIELDS:
        value = values.get(key)
        if value is None:
            continue
        try:
            number = float(value)
        except (TypeError, ValueError) as error:
            raise TypeError(f"Table style option '{key}' must be numeric.") from error
        if number < 0:
            raise ValueError(f"Table style option '{key}' must not be negative.")
