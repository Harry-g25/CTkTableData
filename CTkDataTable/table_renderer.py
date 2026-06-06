"""Canvas drawing helpers for CTkDataTable."""

from __future__ import annotations

import math
import re
import tkinter as tk
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any, Literal

from ._utils import parse_datetime
from .table_column import BadgeStyle, TableColumn


@dataclass(frozen=True)
class ActionRegion:
    """Hit-test rectangle for a Canvas-rendered interactive cell area."""

    row_index: int
    column_key: str
    action_key: str
    bounds: tuple[float, float, float, float]
    kind: Literal["action", "link", "checkbox"] = "action"


class TableRenderer:
    """Draw table headers, rows, and typed cells onto a tkinter Canvas."""

    DEFAULT_CELL_PADDING_X = 12
    DEFAULT_BADGE_PADDING_X = 10
    DEFAULT_BUTTON_PADDING_X = 12
    DEFAULT_CHECKBOX_RADIUS = 4.0
    DEFAULT_ACTION_RADIUS = 5.0

    def __init__(
        self,
        canvas: tk.Canvas,
        font: Any,
        header_font: Any,
        color_resolver: Callable[[Any], str] | None = None,
    ) -> None:
        """Initialize the renderer with a target Canvas and fonts."""

        self.canvas = canvas
        self.font = font
        self.header_font = header_font
        self._resolve_color = color_resolver or (lambda color: str(color))
        self.cell_padding_x: float = self.DEFAULT_CELL_PADDING_X
        self.badge_padding_x: float = self.DEFAULT_BADGE_PADDING_X
        self.button_padding_x: float = self.DEFAULT_BUTTON_PADDING_X
        self.badge_radius: float | None = None
        self.checkbox_radius: float = self.DEFAULT_CHECKBOX_RADIUS
        self.progress_radius: float | None = None
        self.pill_radius: float | None = None
        self.action_radius: float = self.DEFAULT_ACTION_RADIUS
        self._fit_text_cache: dict[tuple[int, str, float], str] = {}
        self._fit_text_cache_limit = 2048

    def configure_style(
        self,
        *,
        cell_padding_x: float | None = None,
        badge_padding_x: float | None = None,
        button_padding_x: float | None = None,
        badge_radius: float | None = None,
        checkbox_radius: float | None = None,
        progress_radius: float | None = None,
        pill_radius: float | None = None,
        action_radius: float | None = None,
    ) -> None:
        """Apply table-wide spacing and radius options."""

        self.cell_padding_x = self._dimension(cell_padding_x, self.DEFAULT_CELL_PADDING_X)
        self.badge_padding_x = self._dimension(badge_padding_x, self.DEFAULT_BADGE_PADDING_X)
        self.button_padding_x = self._dimension(button_padding_x, self.DEFAULT_BUTTON_PADDING_X)
        self.badge_radius = self._optional_dimension(badge_radius)
        self.checkbox_radius = self._dimension(checkbox_radius, self.DEFAULT_CHECKBOX_RADIUS)
        self.progress_radius = self._optional_dimension(progress_radius)
        self.pill_radius = self._optional_dimension(pill_radius)
        self.action_radius = self._dimension(action_radius, self.DEFAULT_ACTION_RADIUS)
        self._fit_text_cache.clear()

    def draw_surface(
        self,
        *,
        canvas_width: int,
        canvas_height: int,
        radius: float,
        colors: Mapping[str, str],
    ) -> None:
        """Draw the rounded table surface behind headers and rows."""

        self.canvas.delete("table_surface")
        if canvas_width <= 0 or canvas_height <= 0:
            return

        radius = self._bounded_radius(radius, canvas_width, canvas_height)
        self._rounded_rectangle(
            0,
            0,
            canvas_width,
            canvas_height,
            radius=radius,
            fill=colors["surface_bg"],
            outline="",
            tags=("table_surface",),
        )
        self.canvas.tag_lower("table_surface")

    def draw_chrome(
        self,
        *,
        canvas_width: int,
        canvas_height: int,
        radius: float,
        border_width: float,
        colors: Mapping[str, str],
        bottom_cap_height: float = 0,
    ) -> None:
        """Mask square canvas corners and draw the table border."""

        self.canvas.delete("table_chrome")
        if canvas_width <= 0 or canvas_height <= 0:
            return

        radius = self._bounded_radius(radius, canvas_width, canvas_height)
        border_width = max(0.0, float(border_width))
        bottom_cap_height = max(0.0, min(float(bottom_cap_height), canvas_height))

        if bottom_cap_height > 0:
            self.canvas.create_rectangle(
                0,
                canvas_height - bottom_cap_height,
                canvas_width,
                canvas_height,
                fill=colors["surface_bg"],
                outline="",
                tags=("table_chrome", "bottom_cap"),
            )

        if radius > 0:
            self._draw_corner_masks(
                canvas_width,
                canvas_height,
                radius,
                background=colors["canvas_bg"],
                tags=("table_chrome", "corner_mask"),
            )

        if border_width > 0:
            inset = border_width / 2
            self._rounded_rectangle(
                inset,
                inset,
                canvas_width - inset,
                canvas_height - inset,
                radius=max(0.0, radius - inset),
                fill="",
                outline=colors["table_border"],
                tags=("table_chrome", "table_border"),
                width=border_width,
            )
        self.canvas.tag_raise("table_chrome")

    def draw_header(
        self,
        columns: list[TableColumn],
        *,
        x_offset: float,
        canvas_width: int,
        header_height: int,
        radius: float,
        sort_key: str | None,
        sort_ascending: bool,
        filtered_column_keys: set[str] | None = None,
        colors: Mapping[str, str],
    ) -> None:
        """Draw the fixed table header row."""

        filtered_column_keys = filtered_column_keys or set()
        self._draw_top_background(
            0,
            0,
            canvas_width,
            header_height,
            radius=radius,
            fill=colors["header_bg"],
            tags=("header", "header_background"),
        )

        x = -x_offset
        for column in columns:
            left = x
            right = x + column.width
            x = right
            if right < 0 or left > canvas_width:
                continue

            column_tag = _tag_value(column.key)
            self.canvas.create_line(
                right,
                8,
                right,
                header_height - 8,
                fill=colors["header_divider"],
                tags=("header", f"header_divider_{column_tag}"),
            )

            indicator_width = 16 if column.key == sort_key else 0
            filter_width = 12 if column.key in filtered_column_keys else 0
            max_text_width = max(0, column.width - (self.cell_padding_x * 2) - indicator_width)
            max_text_width = max(0, max_text_width - filter_width)
            text = self._fit_text(column.title, max_text_width, self.header_font)
            text_x, anchor = self._text_position(left, column.width - indicator_width - filter_width, column.align)
            self.canvas.create_text(
                text_x,
                header_height / 2,
                text=text,
                anchor=anchor,
                fill=colors["header_text"],
                font=self.header_font,
                tags=("header", f"header_text_{column_tag}"),
            )

            if column.key == sort_key:
                self._draw_sort_indicator(
                    right - self.cell_padding_x - 8,
                    header_height / 2,
                    ascending=sort_ascending,
                    color=colors["sort_indicator"],
                    tags=("header", f"sort_{column_tag}"),
                )
            if column.key in filtered_column_keys:
                self.canvas.create_oval(
                    right - self.cell_padding_x - indicator_width - 8,
                    header_height / 2 - 4,
                    right - self.cell_padding_x - indicator_width,
                    header_height / 2 + 4,
                    fill=colors["filter_indicator"],
                    outline="",
                    tags=("header", f"filter_{column_tag}"),
                )

        self.canvas.create_line(
            0,
            header_height - 1,
            canvas_width,
            header_height - 1,
            fill=colors["divider"],
            tags=("header", "header_bottom_divider"),
        )

    def draw_footer(
        self,
        columns: list[TableColumn],
        summaries: Mapping[str, str],
        *,
        x_offset: float,
        canvas_width: int,
        footer_top: int,
        footer_height: int,
        radius: float,
        colors: Mapping[str, str],
    ) -> None:
        """Draw a fixed summary footer row."""

        self.canvas.delete("footer")
        self._draw_bottom_background(
            0,
            footer_top,
            canvas_width,
            footer_top + footer_height,
            radius=radius,
            fill=colors["footer_bg"],
            tags=("footer", "footer_background"),
        )
        self.canvas.create_line(
            0,
            footer_top,
            canvas_width,
            footer_top,
            fill=colors["divider"],
            tags=("footer", "footer_top_divider"),
        )

        x = -x_offset
        for column in columns:
            left = x
            right = x + column.width
            x = right
            if right < 0 or left > canvas_width:
                continue

            column_tag = _tag_value(column.key)
            self.canvas.create_line(
                right,
                footer_top + 8,
                right,
                footer_top + footer_height - 8,
                fill=colors["header_divider"],
                tags=("footer", f"footer_divider_{column_tag}"),
            )
            text = summaries.get(column.key, "")
            if not text:
                continue
            fitted = self._fit_text(text, max(0, column.width - self.cell_padding_x * 2), self.header_font)
            text_x, anchor = self._text_position(left, column.width, column.align)
            self.canvas.create_text(
                text_x,
                footer_top + footer_height / 2,
                text=fitted,
                anchor=anchor,
                fill=colors["footer_text"],
                font=self.header_font,
                tags=("footer", f"footer_text_{column_tag}"),
            )

    def draw_row(
        self,
        row_index: int,
        row: Mapping[str, Any],
        columns: list[TableColumn],
        *,
        y: float,
        row_height: int,
        x_offset: float,
        canvas_width: int,
        selected: bool,
        hovered: bool,
        row_style: Mapping[str, Any] | None = None,
        cell_styles: Mapping[str, Mapping[str, Any]] | None = None,
        colors: Mapping[str, str],
    ) -> list[ActionRegion]:
        """Draw a single visible table row and return any action hit regions."""

        row_tag = f"row_{row_index}"
        if selected and hovered:
            row_bg = colors["selected_hover_bg"]
        elif selected:
            row_bg = colors["selected_bg"]
        elif hovered:
            row_bg = colors["hover_bg"]
        elif row_style and row_style.get("fg_color") is not None:
            row_bg = self._resolve_color(row_style["fg_color"])
        elif row_index % 2:
            row_bg = colors["row_alt_bg"]
        else:
            row_bg = colors["row_bg"]

        if selected and hovered:
            row_text_color = colors["selected_hover_text"]
        elif selected:
            row_text_color = colors["selected_text"]
        elif hovered:
            row_text_color = colors["hover_text"]
        else:
            row_text_color = None
        if row_style and row_style.get("text_color") is not None:
            row_text_color = self._resolve_color(row_style["text_color"])

        self.canvas.create_rectangle(
            0,
            y,
            canvas_width,
            y + row_height,
            fill=row_bg,
            outline="",
            tags=("body", row_tag, "row_background"),
        )

        regions: list[ActionRegion] = []
        x = -x_offset
        for column in columns:
            left = x
            right = x + column.width
            x = right
            if right < 0 or left > canvas_width:
                continue
            regions.extend(
                self._draw_cell(
                    row_index,
                    row,
                    column,
                    left=left,
                    y=y,
                    width=column.width,
                    height=row_height,
                    row_text_color=row_text_color,
                    cell_style=(cell_styles or {}).get(column.key),
                    colors=colors,
                )
            )

        self.canvas.create_line(
            0,
            y + row_height - 1,
            canvas_width,
            y + row_height - 1,
            fill=colors["divider"],
            tags=("body", row_tag, "row_divider"),
        )
        return regions

    def measure_action_regions(
        self,
        row_index: int,
        column: TableColumn,
        *,
        left: float,
        y: float,
        width: int,
        height: int,
    ) -> list[ActionRegion]:
        """Return action button hit regions for a cell without drawing it."""

        if column.type != "action" or not column.actions:
            return []
        return self._action_regions(row_index, column, left=left, y=y, width=width, height=height)

    def _draw_cell(
        self,
        row_index: int,
        row: Mapping[str, Any],
        column: TableColumn,
        *,
        left: float,
        y: float,
        width: int,
        height: int,
        row_text_color: str | None,
        cell_style: Mapping[str, Any] | None,
        colors: Mapping[str, str],
    ) -> list[ActionRegion]:
        value = row.get(column.key)
        column_tag = _tag_value(column.key)
        tags = ("body", f"row_{row_index}", f"cell_{row_index}_{column_tag}")
        if cell_style and cell_style.get("fg_color") is not None:
            self.canvas.create_rectangle(
                left,
                y,
                left + width,
                y + height,
                fill=self._resolve_color(cell_style["fg_color"]),
                outline="",
                tags=tags + ("cell_background",),
            )
        cell_text_color = row_text_color
        if cell_style and cell_style.get("text_color") is not None:
            cell_text_color = self._resolve_color(cell_style["text_color"])

        if column.type == "badge":
            self._draw_badge(value, row, column, left, y, width, height, colors, tags, text_color=cell_text_color)
            return []
        if column.type == "checkbox":
            return self._draw_checkbox(row_index, column.key, bool(value), left, y, width, height, colors, tags)
        if column.type == "progress":
            self._draw_progress(value, column, left, y, width, height, colors, tags)
            return []
        if column.type == "action":
            return self._draw_actions(row_index, column, left, y, width, height, colors, tags)
        if column.type == "pill_list":
            self._draw_pill_list(value, column, left, y, width, height, colors, tags, text_color=cell_text_color)
            return []
        if column.type == "link":
            return self._draw_link(
                row_index,
                value,
                row,
                column,
                left,
                y,
                width,
                height,
                colors,
                tags,
                text_color=cell_text_color,
            )

        text = self._format_value(value, row, column)
        align = (
            "right"
            if column.type in {"number", "percentage", "currency"} and column.align == "left"
            else column.align
        )
        max_width = max(0, width - (self.cell_padding_x * 2))
        fitted = self._fit_text(text, max_width, self.font)
        text_x, anchor = self._text_position(left, width, align)
        self.canvas.create_text(
            text_x,
            y + height / 2,
            text=fitted,
            anchor=anchor,
            fill=cell_text_color or colors["text"],
            font=self.font,
            tags=tags,
        )
        return []

    def _draw_badge(
        self,
        value: Any,
        row: Mapping[str, Any],
        column: TableColumn,
        left: float,
        y: float,
        width: int,
        height: int,
        colors: Mapping[str, str],
        tags: tuple[str, ...],
        *,
        text_color: str | None = None,
    ) -> None:
        style = self._resolve_badge_style(value, row, column, colors)
        text = self._fit_text(style.text, max(0, width - self.cell_padding_x * 2), self.font)
        text_width = min(self.font.measure(text), max(0, width - self.cell_padding_x * 2))
        badge_width = min(width - self.cell_padding_x * 2, text_width + self.badge_padding_x * 2)
        badge_height = min(26, max(20, height - 14))

        if column.align == "right":
            badge_left = left + width - self.cell_padding_x - badge_width
        elif column.align == "center":
            badge_left = left + (width - badge_width) / 2
        else:
            badge_left = left + self.cell_padding_x

        badge_top = y + (height - badge_height) / 2
        self._rounded_rectangle(
            badge_left,
            badge_top,
            badge_left + badge_width,
            badge_top + badge_height,
            radius=self._shape_radius(self.badge_radius, badge_height / 2, badge_width, badge_height),
            fill=self._resolve_color(style.fill_color),
            outline="",
            tags=tags + (f"badge_{_tag_value(column.key)}",),
        )
        self.canvas.create_text(
            badge_left + badge_width / 2,
            y + height / 2,
            text=text,
            anchor="center",
            fill=text_color
            or (self._resolve_color(style.text_color) if style.text_color is not None else colors["badge_text"]),
            font=self.font,
            tags=tags + (f"badge_text_{_tag_value(column.key)}",),
        )

    def _draw_checkbox(
        self,
        row_index: int,
        column_key: str,
        checked: bool,
        left: float,
        y: float,
        width: int,
        height: int,
        colors: Mapping[str, str],
        tags: tuple[str, ...],
    ) -> list[ActionRegion]:
        box_size = min(18, max(14, height - 18))
        box_left = left + (width - box_size) / 2
        box_top = y + (height - box_size) / 2
        fill = colors["checkbox_fill_checked"] if checked else colors["checkbox_fill"]
        self._rounded_rectangle(
            box_left,
            box_top,
            box_left + box_size,
            box_top + box_size,
            radius=self._shape_radius(self.checkbox_radius, self.DEFAULT_CHECKBOX_RADIUS, box_size, box_size),
            fill=fill,
            outline=colors["checkbox_border"],
            tags=tags + ("checkbox",),
        )
        if checked:
            check_points = [
                box_left + box_size * 0.25,
                box_top + box_size * 0.52,
                box_left + box_size * 0.43,
                box_top + box_size * 0.70,
                box_left + box_size * 0.76,
                box_top + box_size * 0.30,
            ]
            self.canvas.create_line(
                check_points,
                fill=colors["checkbox_check"],
                width=2,
                capstyle="round",
                joinstyle="round",
                tags=tags + ("checkbox_check",),
            )
        hit_padding = 4
        return [
            ActionRegion(
                row_index=row_index,
                column_key=column_key,
                action_key="checkbox",
                bounds=(
                    max(left, box_left - hit_padding),
                    max(y, box_top - hit_padding),
                    min(left + width, box_left + box_size + hit_padding),
                    min(y + height, box_top + box_size + hit_padding),
                ),
                kind="checkbox",
            )
        ]

    def _draw_progress(
        self,
        value: Any,
        column: TableColumn,
        left: float,
        y: float,
        width: int,
        height: int,
        colors: Mapping[str, str],
        tags: tuple[str, ...],
    ) -> None:
        number = self._float_value(value)
        if number is None:
            return

        span = column.progress_max - column.progress_min
        ratio = min(1.0, max(0.0, (number - column.progress_min) / span))
        percent = ratio * 100
        bar_width = max(0.0, width - self.cell_padding_x * 2)
        if bar_width <= 0:
            return

        bar_height = min(18, max(12, height - 18))
        bar_left = left + self.cell_padding_x
        bar_top = y + (height - bar_height) / 2
        track_color = (
            self._resolve_color(column.progress_background_color)
            if column.progress_background_color is not None
            else colors["progress_bg"]
        )
        fill_color = (
            self._resolve_color(column.progress_color) if column.progress_color is not None else colors["progress_fill"]
        )
        self._rounded_rectangle(
            bar_left,
            bar_top,
            bar_left + bar_width,
            bar_top + bar_height,
            radius=self._shape_radius(self.progress_radius, bar_height / 2, bar_width, bar_height),
            fill=track_color,
            outline="",
            tags=tags + ("progress_track",),
        )
        fill_width = bar_width * ratio
        if fill_width > 0:
            self._rounded_rectangle(
                bar_left,
                bar_top,
                bar_left + fill_width,
                bar_top + bar_height,
                radius=self._shape_radius(self.progress_radius, bar_height / 2, fill_width, bar_height),
                fill=fill_color,
                outline="",
                tags=tags + ("progress_fill",),
            )

        if not column.progress_show_text:
            return
        try:
            text = column.progress_text_format.format(
                value=number,
                minimum=column.progress_min,
                maximum=column.progress_max,
                min=column.progress_min,
                max=column.progress_max,
                percent=percent,
                ratio=ratio,
            )
        except (KeyError, IndexError, ValueError):
            text = f"{percent:.0f}%"
        fitted = self._fit_text(text, max(0, bar_width - 6), self.font)
        self.canvas.create_text(
            bar_left + bar_width / 2,
            y + height / 2,
            text=fitted,
            anchor="center",
            fill=colors["progress_text"],
            font=self.font,
            tags=tags + ("progress_text",),
        )

    def _draw_link(
        self,
        row_index: int,
        value: Any,
        row: Mapping[str, Any],
        column: TableColumn,
        left: float,
        y: float,
        width: int,
        height: int,
        colors: Mapping[str, str],
        tags: tuple[str, ...],
        *,
        text_color: str | None = None,
    ) -> list[ActionRegion]:
        text = self._format_value(value, row, column)
        if not text:
            return []

        max_width = max(0, width - self.cell_padding_x * 2)
        fitted = self._fit_text(text, max_width, self.font)
        if not fitted:
            return []

        text_x, anchor = self._text_position(left, width, column.align)
        link_color = (
            text_color
            or (self._resolve_color(column.link_color) if column.link_color is not None else colors["link_text"])
        )
        self.canvas.create_text(
            text_x,
            y + height / 2,
            text=fitted,
            anchor=anchor,
            fill=link_color,
            font=self.font,
            tags=tags + ("link_text",),
        )

        text_width = min(self.font.measure(fitted), max_width)
        if anchor == "e":
            text_left = text_x - text_width
            text_right = text_x
        elif anchor == "center":
            text_left = text_x - text_width / 2
            text_right = text_x + text_width / 2
        else:
            text_left = text_x
            text_right = text_x + text_width

        underline_y = y + height / 2 + 8
        self.canvas.create_line(
            text_left,
            underline_y,
            text_right,
            underline_y,
            fill=link_color,
            tags=tags + ("link_underline",),
        )
        return [
            ActionRegion(
                row_index=row_index,
                column_key=column.key,
                action_key="link",
                bounds=(max(left, text_left), y + 4, min(left + width, text_right), y + height - 4),
                kind="link",
            )
        ]

    def _draw_pill_list(
        self,
        value: Any,
        column: TableColumn,
        left: float,
        y: float,
        width: int,
        height: int,
        colors: Mapping[str, str],
        tags: tuple[str, ...],
        *,
        text_color: str | None = None,
    ) -> None:
        values = self._pill_values(value)
        if not values:
            return

        gap = 6
        available = max(0.0, width - self.cell_padding_x * 2)
        if available <= 0:
            return
        pill_height = min(24, max(18, height - 16))
        pill_padding = 9

        segments: list[tuple[str, float, str]] = []
        for raw_text in values:
            fitted = self._fit_text(raw_text, max(0, available - pill_padding * 2), self.font)
            pill_width = min(available, self.font.measure(fitted) + pill_padding * 2)
            needed_width = pill_width if not segments else gap + pill_width
            if self._pill_total_width(segments, gap) + needed_width <= available:
                fill_color = self._pill_fill_color(raw_text, column, colors)
                segments.append((fitted, pill_width, fill_color))
            else:
                break

        if not segments:
            return

        while len(segments) < len(values):
            hidden_count = len(values) - len(segments)
            more_text = f"+{hidden_count}"
            more_width = min(available, self.font.measure(more_text) + pill_padding * 2)
            if self._pill_total_width(segments, gap) + gap + more_width <= available:
                segments.append((more_text, more_width, colors["pill_bg"]))
                break
            segments.pop()
            if not segments:
                segments.append((f"+{len(values)}", min(available, more_width), colors["pill_bg"]))
                break

        total_width = self._pill_total_width(segments, gap)
        if column.align == "right":
            cursor = left + width - self.cell_padding_x - total_width
        elif column.align == "center":
            cursor = left + (width - total_width) / 2
        else:
            cursor = left + self.cell_padding_x

        pill_top = y + (height - pill_height) / 2
        pill_text = text_color or (
            self._resolve_color(column.pill_text_color) if column.pill_text_color is not None else colors["pill_text"]
        )
        for text, pill_width, fill_color in segments:
            self._rounded_rectangle(
                cursor,
                pill_top,
                cursor + pill_width,
                pill_top + pill_height,
                radius=self._shape_radius(self.pill_radius, pill_height / 2, pill_width, pill_height),
                fill=fill_color,
                outline="",
                tags=tags + ("pill",),
            )
            self.canvas.create_text(
                cursor + pill_width / 2,
                y + height / 2,
                text=text,
                anchor="center",
                fill=pill_text,
                font=self.font,
                tags=tags + ("pill_text",),
            )
            cursor += pill_width + gap

    def _draw_actions(
        self,
        row_index: int,
        column: TableColumn,
        left: float,
        y: float,
        width: int,
        height: int,
        colors: Mapping[str, str],
        tags: tuple[str, ...],
    ) -> list[ActionRegion]:
        regions = self._action_regions(row_index, column, left=left, y=y, width=width, height=height)
        for region, action in zip(regions, column.actions, strict=True):
            x1, y1, x2, y2 = region.bounds
            button_tags = tags + ("action_button", f"action_{_tag_value(action.key)}")
            action_fill = colors.get(f"action_fill_{action.key}", colors["action_bg"])
            action_border = colors.get(f"action_border_{action.key}", colors["action_border"])
            action_text = colors.get(f"action_text_{action.key}", colors["action_text"])
            self._rounded_rectangle(
                x1,
                y1,
                x2,
                y2,
                radius=self._shape_radius(self.action_radius, self.DEFAULT_ACTION_RADIUS, x2 - x1, y2 - y1),
                fill=action_fill,
                outline=action_border,
                tags=button_tags,
            )
            fitted = self._fit_text(action.label, max(0, (x2 - x1) - self.button_padding_x), self.font)
            self.canvas.create_text(
                (x1 + x2) / 2,
                (y1 + y2) / 2,
                text=fitted,
                anchor="center",
                fill=action_text,
                font=self.font,
                tags=button_tags + ("action_text",),
            )
        return regions

    def _action_regions(
        self,
        row_index: int,
        column: TableColumn,
        *,
        left: float,
        y: float,
        width: int,
        height: int,
    ) -> list[ActionRegion]:
        gap = 6
        button_height = min(28, max(22, height - 12))
        widths = [
            action.width or max(48, self.font.measure(action.label) + self.button_padding_x * 2)
            for action in column.actions
        ]
        total_width = sum(widths) + gap * max(0, len(widths) - 1)
        if total_width > width - self.cell_padding_x * 2 and widths:
            available = max(32, width - self.cell_padding_x * 2 - gap * max(0, len(widths) - 1))
            equal_width = max(32, available / len(widths))
            widths = [min(item_width, equal_width) for item_width in widths]
            total_width = sum(widths) + gap * max(0, len(widths) - 1)

        start_x = left + (width - total_width) / 2
        top = y + (height - button_height) / 2
        regions: list[ActionRegion] = []
        cursor = start_x
        for action, button_width in zip(column.actions, widths, strict=True):
            regions.append(
                ActionRegion(
                    row_index=row_index,
                    column_key=column.key,
                    action_key=action.key,
                    bounds=(cursor, top, cursor + button_width, top + button_height),
                )
            )
            cursor += button_width + gap
        return regions

    def _format_value(self, value: Any, row: Mapping[str, Any], column: TableColumn) -> str:
        if column.formatter is not None:
            try:
                return str(column.formatter(value, row))
            except Exception as error:
                raise RuntimeError(f"Formatter failed for column '{column.key}': {error}") from error
        if value is None:
            return ""
        if column.type == "number":
            return self._format_number(value, column)
        if column.type == "percentage":
            return self._format_percentage(value, column)
        if column.type == "currency":
            return self._format_currency(value, column)
        if column.type == "date":
            return self._format_date(value, column.date_format)
        if column.type == "datetime":
            return self._format_datetime(value, column.datetime_format)
        return str(value)

    def _format_number(self, value: Any, column: TableColumn) -> str:
        if column.number_format is None:
            return str(value)
        if callable(column.number_format):
            return str(column.number_format(value))
        try:
            number = float(value)
        except (TypeError, ValueError):
            return str(value)
        return column.number_format.format(number)

    def _format_percentage(self, value: Any, column: TableColumn) -> str:
        number = self._float_value(value)
        if number is None:
            return str(value)
        display_value = number * column.percentage_multiplier
        try:
            return column.percentage_format.format(
                display_value,
                value=display_value,
                raw_value=number,
                multiplier=column.percentage_multiplier,
            )
        except (KeyError, IndexError, ValueError):
            return str(value)

    def _format_currency(self, value: Any, column: TableColumn) -> str:
        number = self._float_value(value)
        if number is None:
            return str(value)
        template = column.currency_negative_format if number < 0 else column.currency_format
        try:
            return template.format(
                symbol=column.currency_symbol,
                value=abs(number),
                signed_value=number,
            )
        except (KeyError, IndexError, ValueError):
            return str(value)

    def _float_value(self, value: Any) -> float | None:
        try:
            return float(str(value).replace(",", ""))
        except (TypeError, ValueError):
            return None

    def _format_date(self, value: Any, date_format: str) -> str:
        parsed = parse_datetime(value)
        if parsed is None:
            return str(value)
        return parsed.date().strftime(date_format)

    def _format_datetime(self, value: Any, datetime_format: str) -> str:
        parsed = parse_datetime(value)
        if parsed is None:
            return str(value)
        return parsed.strftime(datetime_format)

    def _resolve_badge_style(
        self,
        value: Any,
        row: Mapping[str, Any],
        column: TableColumn,
        colors: Mapping[str, str],
    ) -> BadgeStyle:
        text = "" if value is None else str(value)
        if text in column.badge_colors:
            return BadgeStyle(text=text, fill_color=column.badge_colors[text], text_color=None)
        if column.badge_fallback_handler is not None:
            result = column.badge_fallback_handler(value, row, column)
            if isinstance(result, BadgeStyle):
                return result
            if result is not None:
                return BadgeStyle(text=text, fill_color=result, text_color=None)
        if column.badge_fallback_color is not None:
            return BadgeStyle(text=text, fill_color=column.badge_fallback_color, text_color=None)
        return BadgeStyle(text=text, fill_color=colors["badge_default_bg"], text_color=colors["badge_text"])

    def _pill_values(self, value: Any) -> list[str]:
        if value is None:
            return []
        if isinstance(value, str):
            return [part.strip() for part in value.split(",") if part.strip()]
        if isinstance(value, (list, tuple, set, frozenset)):
            return [str(item) for item in value if str(item)]
        return [str(value)]

    def _pill_fill_color(self, text: str, column: TableColumn, colors: Mapping[str, str]) -> str:
        if text in column.pill_colors:
            return self._resolve_color(column.pill_colors[text])
        if column.pill_fallback_color is not None:
            return self._resolve_color(column.pill_fallback_color)
        return colors["pill_bg"]

    def _pill_total_width(self, segments: list[tuple[str, float, str]], gap: int) -> float:
        if not segments:
            return 0.0
        return sum(segment[1] for segment in segments) + gap * (len(segments) - 1)

    def _text_position(self, left: float, width: float, align: str) -> tuple[float, Literal["e", "center", "w"]]:
        if align == "right":
            return left + width - self.cell_padding_x, "e"
        if align == "center":
            return left + width / 2, "center"
        return left + self.cell_padding_x, "w"

    def _fit_text(self, text: str, max_width: float, font: Any) -> str:
        cache_key = (id(font), text, round(float(max_width), 2))
        cached = self._fit_text_cache.get(cache_key)
        if cached is not None:
            return cached

        if max_width <= 0:
            return self._remember_fit_text(cache_key, "")
        if font.measure(text) <= max_width:
            return self._remember_fit_text(cache_key, text)
        suffix = "..."
        suffix_width = font.measure(suffix)
        if suffix_width > max_width:
            return self._remember_fit_text(cache_key, "")
        low = 0
        high = len(text)
        while low < high:
            mid = (low + high + 1) // 2
            if font.measure(text[:mid] + suffix) <= max_width:
                low = mid
            else:
                high = mid - 1
        return self._remember_fit_text(cache_key, text[:low] + suffix)

    def _remember_fit_text(self, cache_key: tuple[int, str, float], value: str) -> str:
        if len(self._fit_text_cache) >= self._fit_text_cache_limit:
            self._fit_text_cache.clear()
        self._fit_text_cache[cache_key] = value
        return value

    def _dimension(self, value: float | None, fallback: float) -> float:
        if value is None:
            return fallback
        return max(0.0, float(value))

    def _optional_dimension(self, value: float | None) -> float | None:
        if value is None:
            return None
        return max(0.0, float(value))

    def _shape_radius(self, configured: float | None, fallback: float, width: float, height: float) -> float:
        radius = fallback if configured is None else configured
        return self._bounded_radius(radius, max(0.0, width), max(0.0, height))

    def _draw_sort_indicator(self, x: float, y: float, *, ascending: bool, color: str, tags: tuple[str, ...]) -> None:
        size = 8
        if ascending:
            points = (x, y - size / 2, x - size / 2, y + size / 2, x + size / 2, y + size / 2)
        else:
            points = (x, y + size / 2, x - size / 2, y - size / 2, x + size / 2, y - size / 2)
        self.canvas.create_polygon(points, fill=color, outline="", tags=tags)

    def _bounded_radius(self, radius: float, width: float, height: float) -> float:
        return max(0.0, min(float(radius), width / 2, height / 2))

    def _draw_top_background(
        self,
        x1: float,
        y1: float,
        x2: float,
        y2: float,
        *,
        radius: float,
        fill: str,
        tags: tuple[str, ...],
    ) -> None:
        height = max(0.0, y2 - y1)
        radius = self._bounded_radius(radius, x2 - x1, height)
        if radius <= 0:
            self.canvas.create_rectangle(x1, y1, x2, y2, fill=fill, outline="", tags=tags)
            return

        rounded_bottom = min(y2, y1 + radius * 2)
        self._rounded_rectangle(x1, y1, x2, rounded_bottom, radius=radius, fill=fill, outline="", tags=tags)
        self.canvas.create_rectangle(x1, y1 + radius, x2, y2, fill=fill, outline="", tags=tags)

    def _draw_bottom_background(
        self,
        x1: float,
        y1: float,
        x2: float,
        y2: float,
        *,
        radius: float,
        fill: str,
        tags: tuple[str, ...],
    ) -> None:
        height = max(0.0, y2 - y1)
        radius = self._bounded_radius(radius, x2 - x1, height)
        if radius <= 0:
            self.canvas.create_rectangle(x1, y1, x2, y2, fill=fill, outline="", tags=tags)
            return

        rounded_top = max(y1, y2 - radius * 2)
        self.canvas.create_rectangle(x1, y1, x2, y2 - radius, fill=fill, outline="", tags=tags)
        self._rounded_rectangle(x1, rounded_top, x2, y2, radius=radius, fill=fill, outline="", tags=tags)

    def _draw_corner_masks(
        self,
        width: float,
        height: float,
        radius: float,
        *,
        background: str,
        tags: tuple[str, ...],
    ) -> None:
        steps = max(4, min(16, math.ceil(radius / 2)))
        corner_specs = (
            ((0, 0), (0, 0), (radius, 0), (radius, radius), -90, -180),
            ((width, 0), (width, 0), (width, radius), (width - radius, radius), 0, -90),
            ((width, height), (width, height), (width, height - radius), (width - radius, height - radius), 0, 90),
            ((0, height), (0, height), (0, height - radius), (radius, height - radius), 180, 90),
        )
        for corner, first, second, center, start_angle, end_angle in corner_specs:
            points = [
                corner,
                first,
                second,
                *self._arc_points(center, radius, start_angle, end_angle, steps),
                corner,
            ]
            self.canvas.create_polygon(
                self._flatten_points(points),
                fill=background,
                outline="",
                tags=tags,
            )

    def _arc_points(
        self,
        center: tuple[float, float],
        radius: float,
        start_angle: float,
        end_angle: float,
        steps: int,
    ) -> list[tuple[float, float]]:
        cx, cy = center
        return [
            (
                cx + radius * math.cos(math.radians(start_angle + (end_angle - start_angle) * index / steps)),
                cy + radius * math.sin(math.radians(start_angle + (end_angle - start_angle) * index / steps)),
            )
            for index in range(steps + 1)
        ]

    def _flatten_points(self, points: list[tuple[float, float]]) -> tuple[float, ...]:
        return tuple(coord for point in points for coord in point)

    def _rounded_rectangle(
        self,
        x1: float,
        y1: float,
        x2: float,
        y2: float,
        *,
        radius: float,
        fill: str,
        outline: str,
        tags: tuple[str, ...],
        width: float = 1,
    ) -> None:
        radius = max(0, min(radius, (x2 - x1) / 2, (y2 - y1) / 2))
        points = (
            x1 + radius,
            y1,
            x2 - radius,
            y1,
            x2,
            y1,
            x2,
            y1 + radius,
            x2,
            y2 - radius,
            x2,
            y2,
            x2 - radius,
            y2,
            x1 + radius,
            y2,
            x1,
            y2,
            x1,
            y2 - radius,
            x1,
            y1 + radius,
            x1,
            y1,
        )
        self.canvas.create_polygon(points, smooth=True, fill=fill, outline=outline, tags=tags, width=width)


def _tag_value(value: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_]", "_", value)
