"""Realistic NCR records demo for CTkDataTable."""

from __future__ import annotations

import sys
from datetime import date, timedelta
from pathlib import Path

import customtkinter as ctk

try:
    from CTkDataTable import CTkDataTable, TableRowEvent
except ModuleNotFoundError as error:
    if error.name != "CTkDataTable":
        raise
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    from CTkDataTable import CTkDataTable, TableRowEvent


def main() -> None:
    """Run the NCR records table demo."""

    ctk.set_appearance_mode("System")
    ctk.set_default_color_theme("blue")

    app = ctk.CTk()
    app.title("NCR Records")
    app.geometry("1040x580")
    app.grid_rowconfigure(1, weight=1)
    app.grid_columnconfigure(0, weight=1)

    toolbar = ctk.CTkFrame(app, corner_radius=0)
    toolbar.grid(row=0, column=0, sticky="ew", padx=14, pady=(14, 8))
    toolbar.grid_columnconfigure(0, weight=1)

    search = ctk.CTkEntry(toolbar, placeholder_text="Search NCR records")
    search.grid(row=0, column=0, sticky="ew", padx=10, pady=10)
    status = ctk.CTkLabel(toolbar, text="Ready", anchor="w")
    status.grid(row=1, column=0, sticky="ew", padx=10, pady=(0, 10))

    columns = [
        {"key": "id", "title": "NCR ID", "width": 105, "type": "text"},
        {"key": "title", "title": "Title", "width": 285, "type": "text"},
        {
            "key": "status",
            "title": "Status",
            "width": 130,
            "type": "badge",
            "badge_colors": {"Open": "#2ecc71", "In Review": "#3498db", "Closed": "#95a5a6", "Overdue": "#e67e22"},
            "badge_fallback_color": "#64748b",
        },
        {
            "key": "priority",
            "title": "Priority",
            "width": 115,
            "type": "badge",
            "badge_colors": {"Critical": "#dc2626", "High": "#f97316", "Medium": "#f59e0b", "Low": "#22c55e"},
            "badge_fallback_color": "#64748b",
        },
        {"key": "assigned_to", "title": "Assigned To", "width": 160, "type": "text"},
        {"key": "created", "title": "Date Created", "width": 130, "type": "date"},
        {
            "key": "actions",
            "title": "Actions",
            "width": 150,
            "type": "action",
            "sortable": False,
            "actions": [{"key": "view", "label": "View"}, {"key": "delete", "label": "Delete"}],
        },
    ]

    today = date.today()
    rows = [
        {
            "id": "NCR-2026-001",
            "title": "Supplier certificate mismatch",
            "status": "Open",
            "priority": "High",
            "assigned_to": "Amelia Hart",
            "created": today - timedelta(days=2),
        },
        {
            "id": "NCR-2026-002",
            "title": "Dimensional tolerance outside specification",
            "status": "In Review",
            "priority": "Critical",
            "assigned_to": "Noah Singh",
            "created": today - timedelta(days=5),
        },
        {
            "id": "NCR-2026-003",
            "title": "Packaging label missing batch code",
            "status": "Closed",
            "priority": "Low",
            "assigned_to": "Grace Miller",
            "created": today - timedelta(days=13),
        },
        {
            "id": "NCR-2026-004",
            "title": "Calibration record overdue",
            "status": "Overdue",
            "priority": "Medium",
            "assigned_to": "Liam Carter",
            "created": today - timedelta(days=19),
        },
    ]
    for index in range(60):
        rows.append(
            {
                "id": f"NCR-2026-{index + 5:03d}",
                "title": [
                    "Surface finish variance on incoming component",
                    "Inspection sample failed functional test",
                    "Missing containment evidence",
                    "Material traceability gap",
                ][index % 4],
                "status": ["Open", "In Review", "Closed", "Overdue"][index % 4],
                "priority": ["Low", "Medium", "High", "Critical"][index % 4],
                "assigned_to": ["Amelia Hart", "Noah Singh", "Grace Miller", "Liam Carter"][index % 4],
                "created": today - timedelta(days=index + 1),
            }
        )

    table: CTkDataTable | None = None

    def handle_action(event: TableRowEvent) -> None:
        if table is None:
            return
        if event.action_key == "view":
            status.configure(text=f"Viewing {event.row['id']}")
            return
        if event.action_key == "delete":
            table.delete_row_by_key("id", event.row["id"])
            status.configure(text=f"Deleted {event.row['id']}")

    def handle_context(event: TableRowEvent) -> None:
        if event.action_key == "copy_id":
            app.clipboard_clear()
            app.clipboard_append(str(event.row["id"]))
            status.configure(text=f"Copied {event.row['id']}")
        elif event.action_key == "view":
            status.configure(text=f"Viewing {event.row['id']}")

    table = CTkDataTable(
        app,
        columns=columns,
        data=rows,
        horizontal_scroll=True,
        resizable_columns=True,
        context_menu=[
            {"key": "copy_id", "label": "Copy NCR ID"},
            {"key": "view", "label": "View"},
        ],
        on_action_click=handle_action,
        on_context_action=handle_context,
        footer=True,
        summaries={"id": lambda visible_rows: f"{len(visible_rows)} records"},
    )
    table.grid(row=1, column=0, sticky="nsew", padx=14, pady=(0, 14))

    search.bind("<KeyRelease>", lambda _event: table.search(search.get()))
    app.mainloop()


if __name__ == "__main__":
    main()
