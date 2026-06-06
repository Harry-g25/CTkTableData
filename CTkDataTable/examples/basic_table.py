"""Standalone CTkDataTable demo showing the core Phase 1 features."""

from __future__ import annotations

import sys
from collections.abc import Mapping
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

import customtkinter as ctk

try:
    from CTkDataTable import BadgeStyle, Column, CTkDataTable, TableColumn
except ModuleNotFoundError as error:
    if error.name != "CTkDataTable":
        raise
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    from CTkDataTable import BadgeStyle, Column, CTkDataTable, TableColumn


def unknown_badge(value: Any, _row: Mapping[str, Any], _column: TableColumn) -> BadgeStyle:
    """Return a fallback badge style for unmapped values."""

    return BadgeStyle(text=str(value), fill_color=("#64748b", "#475569"), text_color=("#ffffff", "#ffffff"))


def highlight_overdue(row: dict[str, Any]) -> dict[str, Any] | None:
    """Highlight overdue rows when style hooks are enabled."""

    if row.get("status") == "Overdue":
        return {"fg_color": ("#fff7ed", "#431407")}
    return None


def style_amount(_row: dict[str, Any], column_key: str, value: Any) -> dict[str, Any] | None:
    """Tint large amount cells when style hooks are enabled."""

    if column_key == "amount" and isinstance(value, (int, float)) and value >= 9000:
        return {"text_color": ("#b45309", "#fbbf24")}
    return None


def main() -> None:
    """Run the basic table demo."""

    ctk.set_appearance_mode("System")
    ctk.set_default_color_theme("blue")

    app = ctk.CTk()
    app.title("CTkDataTable Basic Demo")
    app.geometry("1120x640")
    app.grid_columnconfigure(0, weight=1)
    app.grid_rowconfigure(0, weight=1)
    status = ctk.CTkLabel(app, text="Ready", anchor="w")
    status.grid(row=1, column=0, sticky="ew", padx=14, pady=(0, 8))

    today = date.today()
    columns = [
        Column("name").title("Customer").width(180),
        Column("amount").title("Amount").width(120).currency(),
        Column("completion").title("Complete").width(140).progress(),
        Column("due").title("Due Date").width(130).date(),
        Column("updated").title("Updated").width(170).datetime(),
        Column("status").title("Status").width(130).badge(
            colors={"Open": "#2ecc71", "Closed": "#e74c3c", "Overdue": "#e67e22"},
            fallback_handler=unknown_badge,
        ),
        Column("priority").title("Priority").width(110).badge(
            colors={"High": "#ef4444", "Medium": "#f59e0b", "Low": "#22c55e"},
            fallback_color="#64748b",
        ),
        Column("tags").title("Tags").width(190).pill_list(
            colors={"Renewal": "#0ea5e9", "Finance": "#8b5cf6", "Risk": "#ef4444", "Ops": "#22c55e"},
            fallback_color="#64748b",
            text_color="#ffffff",
        ),
        Column("approved").title("Approved").width(100).checkbox(),
        Column("profile").title("Profile").width(130).link(),
        Column("actions").title("Actions").width(170).action(
            buttons=[{"key": "view", "label": "View"}, {"key": "archive", "label": "Archive"}],
        ),
    ]
    rows = [
        {
            "name": "Northwind Components",
            "amount": 12640.50,
            "completion": 72,
            "due": today + timedelta(days=3),
            "updated": datetime.now() - timedelta(hours=2),
            "status": "Open",
            "priority": "High",
            "tags": ["Renewal", "Finance"],
            "approved": False,
            "profile": "Open profile",
        },
        {
            "name": "Meridian Foods",
            "amount": 7320,
            "completion": 43,
            "due": today - timedelta(days=1),
            "updated": datetime.now() - timedelta(days=1, hours=3),
            "status": "Overdue",
            "priority": "Medium",
            "tags": ["Risk", "Supplier"],
            "approved": True,
            "profile": "Open profile",
        },
        {
            "name": "Blue Ridge Logistics",
            "amount": 1895.99,
            "completion": 100,
            "due": today + timedelta(days=11),
            "updated": datetime.now() - timedelta(minutes=35),
            "status": "Closed",
            "priority": "Low",
            "tags": ["Ops", "Complete"],
            "approved": True,
            "profile": "Open profile",
        },
        {
            "name": "Aster Digital",
            "amount": 9842.75,
            "completion": 58,
            "due": today + timedelta(days=6),
            "updated": datetime.now() - timedelta(days=2),
            "status": "Waiting",
            "priority": "Medium",
            "tags": "Renewal, Ops",
            "approved": False,
            "profile": "Open profile",
        },
    ]

    for index in range(800):
        rows.append(
            {
                "name": f"Demo Account {index + 1:03d}",
                "amount": 1200 + index * 37.5,
                "completion": (index * 7) % 101,
                "due": today + timedelta(days=index % 21),
                "updated": datetime.now() - timedelta(hours=index),
                "status": ["Open", "Closed", "Overdue", "Waiting"][index % 4],
                "priority": ["Low", "Medium", "High"][index % 3],
                "tags": [["Ops"], ["Finance", "Renewal"], ["Risk"], ["Support", "Review"]][index % 4],
                "approved": index % 2 == 0,
                "profile": "Open profile",
            }
        )

    def show_status(message: str) -> None:
        status.configure(text=message)

    def show_row_status(event: Any) -> None:
        show_status(f"Selected row: {event.row.get('name')}")

    def show_cell_status(event: Any) -> None:
        value = event.row.get(event.column_key or "")
        show_status(f"Selected cell: {event.column_key} = {value}")

    def show_sort_status(key: str, ascending: bool) -> None:
        direction = "ascending" if ascending else "descending"
        show_status(f"Sorted {key} {direction}")

    def show_search_status(query: str) -> None:
        show_status(f"Search query: {query}")

    def show_action_status(event: Any) -> None:
        show_status(f"Action {event.action_key}: {event.row.get('name')}")

    def show_link_status(event: Any) -> None:
        show_status(f"Link {event.column_key}: {event.row.get('name')}")

    table = CTkDataTable(
        app,
        columns=columns,
        data=rows,
        horizontal_scroll=False,
        multi_select=False,
        searchable=False,
        search_delay_ms=120,
        resizable_columns=True,
        enable_style_hooks=True,
        row_style=highlight_overdue,
        cell_style=style_amount,
        footer=False,
        summaries={"name": lambda visible_rows: f"{len(visible_rows)} rows", "amount": "sum"},
        on_row_click=show_row_status,
        on_cell_click=show_cell_status,
        on_sort=show_sort_status,
        on_search=show_search_status,
        on_action_click=show_action_status,
        on_link_click=show_link_status,
    )
    table.grid(row=0, column=0, sticky="nsew", padx=14, pady=14)

    def toggle_mode() -> None:
        ctk.set_appearance_mode("Dark" if ctk.get_appearance_mode() == "Light" else "Light")
        table.refresh()

    mode_btn = ctk.CTkButton(app, text="Toggle Dark/Light", command=toggle_mode)
    mode_btn.grid(row=2, column=0, pady=(0, 10))

    app.mainloop()


if __name__ == "__main__":
    main()
