# CTkDataTable User Guide and API Reference

`CTkDataTable` is a virtualized data table for CustomTkinter. Use it when you want to show records from Python lists, database queries, reports, admin screens, dashboards, or audit logs without creating one Tkinter widget for every cell.

The table renders only the visible body rows, so large datasets stay responsive. Your full row list is still kept in memory.

## What You Need First

Install the package in your environment, then import the widget:

```python
import customtkinter as ctk

from CTkDataTable import CTkDataTable
```

Optional public helpers:

```python
from CTkDataTable import BadgeStyle, Column, TableAction, TableColumn, TableRowEvent, TableStyle, rows_from_cursor
```

Use the table in three steps:

1. Define `columns`.
2. Provide `rows`.
3. Place the table with `grid()`, `pack()`, or `place()`.

The most important rule:

```python
column["key"] == row_dictionary_key
```

For example, this column:

```python
{"key": "name", "title": "Name", "width": 180}
```

reads this value from each row:

```python
{"name": "Alice"}
```

Use the exact same spelling and capitalization. `customer_name` and `customerName` are different keys.

## Entry Point 1: Static Data Display

Use this pattern when you already have a list of records and want to show it.

```python
import customtkinter as ctk

from CTkDataTable import CTkDataTable


app = ctk.CTk()
app.title("Customers")
app.geometry("760x420")
app.grid_columnconfigure(0, weight=1)
app.grid_rowconfigure(0, weight=1)

columns = [
    {"key": "id", "title": "ID", "width": 80, "type": "number"},
    {"key": "name", "title": "Customer", "width": 220},
    {"key": "status", "title": "Status", "width": 140, "type": "badge"},
]

rows = [
    {"id": 1, "name": "Northwind Components", "status": "Open"},
    {"id": 2, "name": "Meridian Foods", "status": "Closed"},
    {"id": 3, "name": "Blue Ridge Logistics", "status": "In Review"},
]

table = CTkDataTable(app, columns=columns, data=rows)
table.grid(row=0, column=0, sticky="nsew", padx=16, pady=16)

app.mainloop()
```

## Entry Point 2: Real-Time Updates

Use `add_row()`, `add_rows()`, `update_row_where()`, and `delete_row_by_key()` when rows change after the table is already visible.

```python
import customtkinter as ctk

from CTkDataTable import CTkDataTable


app = ctk.CTk()
app.title("Live Orders")
app.geometry("820x420")
app.grid_columnconfigure(0, weight=1)
app.grid_rowconfigure(1, weight=1)

columns = [
    {"key": "id", "title": "Order", "width": 100},
    {"key": "customer", "title": "Customer", "width": 220},
    {"key": "status", "title": "Status", "width": 140, "type": "badge"},
    {"key": "amount", "title": "Amount", "width": 120, "type": "currency"},
]

rows = [
    {"id": "SO-1001", "customer": "Northwind Components", "status": "Open", "amount": 1250},
    {"id": "SO-1002", "customer": "Meridian Foods", "status": "Open", "amount": 890},
]

table = CTkDataTable(app, columns=columns, data=rows)
table.grid(row=1, column=0, sticky="nsew", padx=16, pady=(0, 16))


def add_order() -> None:
    table.add_row(
        {"id": "SO-1003", "customer": "Blue Ridge Logistics", "status": "Open", "amount": 1425}
    )


def mark_shipped() -> None:
    table.update_row_where(
        "id",
        "SO-1001",
        {"id": "SO-1001", "customer": "Northwind Components", "status": "Shipped", "amount": 1250},
    )


def remove_order() -> None:
    table.delete_row_by_key("id", "SO-1002")


toolbar = ctk.CTkFrame(app, corner_radius=0)
toolbar.grid(row=0, column=0, sticky="ew", padx=16, pady=(16, 8))
ctk.CTkButton(toolbar, text="Add", command=add_order).grid(row=0, column=0, padx=6, pady=8)
ctk.CTkButton(toolbar, text="Ship SO-1001", command=mark_shipped).grid(row=0, column=1, padx=6, pady=8)
ctk.CTkButton(toolbar, text="Remove SO-1002", command=remove_order).grid(row=0, column=2, padx=6, pady=8)

app.mainloop()
```

## Entry Point 3: Interactive Sorting, Searching, and Filtering

Users can click sortable headers. Your code can also call `sort_by()`, `search()`, and `set_column_filter()`.

```python
import customtkinter as ctk

from CTkDataTable import CTkDataTable, TableRowEvent


app = ctk.CTk()
app.title("Interactive Table")
app.geometry("900x500")
app.grid_columnconfigure(0, weight=1)
app.grid_rowconfigure(2, weight=1)

status = ctk.CTkLabel(app, text="No selection", anchor="w")
status.grid(row=0, column=0, sticky="ew", padx=16, pady=(16, 4))

search = ctk.CTkEntry(app, placeholder_text="Search visible columns")
search.grid(row=1, column=0, sticky="ew", padx=16, pady=(4, 8))

columns = [
    {"key": "id", "title": "ID", "width": 80, "type": "number"},
    {"key": "name", "title": "Customer", "width": 220},
    {"key": "status", "title": "Status", "width": 140, "type": "badge"},
    {"key": "amount", "title": "Amount", "width": 120, "type": "currency"},
]

rows = [
    {"id": 1, "name": "Northwind Components", "status": "Open", "amount": 1250},
    {"id": 2, "name": "Meridian Foods", "status": "Closed", "amount": 890},
    {"id": 3, "name": "Blue Ridge Logistics", "status": "Open", "amount": 1425},
]


def show_selected(event: TableRowEvent) -> None:
    status.configure(
        text=f"Selected source row {event.source_index}, visible row {event.view_index}: {event.row['name']}"
    )


def report_sort(column_key: str, ascending: bool) -> None:
    direction = "ascending" if ascending else "descending"
    status.configure(text=f"Sorted by {column_key} {direction}")


table = CTkDataTable(
    app,
    columns=columns,
    data=rows,
    multi_select=True,
    on_row_click=show_selected,
    on_sort=report_sort,
)
table.grid(row=2, column=0, sticky="nsew", padx=16, pady=(0, 16))

search.bind("<KeyRelease>", lambda _event: table.search(search.get()))

table.set_column_filter("status", {"type": "equals", "value": "Open"})
table.sort_by("amount", ascending=False)

app.mainloop()
```

## Row Data

Rows are converted to dictionaries internally. The table accepts:

| Source row value | How to use it |
| --- | --- |
| `dict` | Pass directly in `data`, `set_data()`, `add_row()`, or `add_rows()`. |
| Any mapping object | Pass directly if it behaves like a dictionary. |
| `sqlite3.Row` | Set `connection.row_factory = sqlite3.Row`, then pass fetched rows directly. |
| SQLAlchemy rows with `_mapping` | Pass fetched result rows directly. |
| PostgreSQL dictionary rows | Use psycopg 3 `dict_row` or psycopg2 `RealDictCursor`, then pass fetched rows directly. |
| Plain DB-API tuple rows | Convert them with `rows_from_cursor(cursor)`. |

Plain tuple rows do not contain column names, so the table cannot use them directly.

### SQLite Rows

```python
import sqlite3


connection = sqlite3.connect("customers.db")
connection.row_factory = sqlite3.Row

rows = connection.execute(
    """
    SELECT id, name, status
    FROM customers
    ORDER BY name
    """
).fetchall()

table.set_data(rows)
```

### DB-API Cursor Rows

```python
from CTkDataTable import rows_from_cursor


cursor.execute(
    """
    SELECT id, name, status
    FROM customers
    ORDER BY name
    """
)

table.set_data(rows_from_cursor(cursor))
```

### SQLAlchemy Rows

```python
from sqlalchemy import text


with engine.connect() as connection:
    result = connection.execute(
        text("SELECT id, name, status FROM customers ORDER BY name")
    )
    table.set_data(result.fetchall())
```

If database column names do not match your table keys, use SQL aliases:

```sql
SELECT customer_id AS id, customer_name AS name, order_status AS status
FROM customers;
```

## Column Definitions

You can define columns with dictionaries, `TableColumn`, or the fluent `Column` builder. Dictionary columns are the shortest option.

```python
columns = [
    {"key": "id", "title": "ID", "width": 80, "type": "number"},
    {"key": "name", "title": "Customer", "width": 220},
]
```

Use `TableColumn` when you prefer typed Python objects:

```python
from CTkDataTable import TableColumn


columns = [
    TableColumn(key="id", title="ID", width=80, type="number"),
    TableColumn(key="name", title="Customer", width=220),
]
```

Use `Column` when you want fluent column setup:

```python
from CTkDataTable import Column


columns = [
    Column("id").title("ID").width(80).number(),
    Column("name").title("Customer").width(220).text(),
    Column("status").title("Status").width(140).badge(
        colors={"Open": "#22c55e", "Closed": "#64748b"},
        fallback_color="#94a3b8",
    ),
]
```

## All Column Types in One App

This complete app demonstrates all 12 column types: `text`, `number`, `percentage`, `currency`, `date`, `datetime`, `badge`, `checkbox`, `progress`, `link`, `pill_list`, and `action`.

```python
from datetime import date, datetime

import customtkinter as ctk

from CTkDataTable import CTkDataTable, TableRowEvent


app = ctk.CTk()
app.title("Column Types")
app.geometry("1180x520")
app.grid_columnconfigure(0, weight=1)
app.grid_rowconfigure(1, weight=1)

message = ctk.CTkLabel(app, text="Click a link or action", anchor="w")
message.grid(row=0, column=0, sticky="ew", padx=16, pady=(16, 8))

columns = [
    {"key": "name", "title": "Text", "width": 180, "type": "text"},
    {"key": "quantity", "title": "Number", "width": 95, "type": "number", "number_format": "{:,.0f}"},
    {"key": "margin", "title": "Percentage", "width": 120, "type": "percentage", "percentage_format": "{value:.1f}%"},
    {"key": "amount", "title": "Currency", "width": 120, "type": "currency", "currency_symbol": "$"},
    {"key": "due_date", "title": "Date", "width": 120, "type": "date", "date_format": "%d %b %Y"},
    {"key": "updated_at", "title": "Datetime", "width": 150, "type": "datetime", "datetime_format": "%d %b %H:%M"},
    {
        "key": "status",
        "title": "Badge",
        "width": 120,
        "type": "badge",
        "badge_colors": {"Open": "#22c55e", "Blocked": "#ef4444"},
        "badge_fallback_color": "#64748b",
    },
    {"key": "approved", "title": "Checkbox", "width": 105, "type": "checkbox"},
    {"key": "progress", "title": "Progress", "width": 145, "type": "progress", "progress_text_format": "{percent:.0f}%"},
    {"key": "profile", "title": "Link", "width": 120, "type": "link"},
    {
        "key": "tags",
        "title": "Pills",
        "width": 170,
        "type": "pill_list",
        "pill_colors": {"Urgent": "#ef4444", "Finance": "#0ea5e9"},
        "pill_fallback_color": "#64748b",
        "pill_text_color": "#ffffff",
    },
    {
        "key": "actions",
        "title": "Action",
        "width": 170,
        "type": "action",
        "sortable": False,
        "actions": [
            {"key": "view", "label": "View"},
            {"key": "delete", "label": "Delete"},
        ],
    },
]

rows = [
    {
        "name": "Northwind Components",
        "quantity": 1200,
        "margin": 18.4,
        "amount": 12640.5,
        "due_date": date(2026, 6, 12),
        "updated_at": datetime(2026, 6, 4, 9, 30),
        "status": "Open",
        "approved": True,
        "progress": 72,
        "profile": "Open",
        "tags": ["Urgent", "Finance"],
        "actions": None,
    },
    {
        "name": "Meridian Foods",
        "quantity": 860,
        "margin": 7.5,
        "amount": -240.75,
        "due_date": "2026-06-18",
        "updated_at": "2026-06-04T15:45:00",
        "status": "Blocked",
        "approved": False,
        "progress": 35,
        "profile": "Open",
        "tags": "Sales, Follow-up",
        "actions": None,
    },
]


def handle_link(event: TableRowEvent) -> None:
    message.configure(text=f"Link clicked for {event.row['name']}")


def handle_action(event: TableRowEvent) -> None:
    message.configure(text=f"{event.action_key} clicked for {event.row['name']}")


table = CTkDataTable(
    app,
    columns=columns,
    data=rows,
    horizontal_scroll=True,
    on_link_click=handle_link,
    on_action_click=handle_action,
)
table.grid(row=1, column=0, sticky="nsew", padx=16, pady=(0, 16))

app.mainloop()
```

## Column Type Reference

Each column type below has a complete runnable example. Copy the whole code block into a Python file and run it from an environment where `customtkinter` and `CTkDataTable` are installed.

Every column type supports these common adjustable options:

| Option | Default | Accepted values | What it changes |
| --- | --- | --- | --- |
| `key` | Required | String row field name. Must match row dictionary keys exactly. | Which row value the column displays. |
| `title` | Title-cased `key` for dictionary columns | String | Header label. |
| `width` | `140` for dictionary columns | Integer greater than `0` | Column width in pixels. |
| `align` | Depends on type | `"left"`, `"center"`, or `"right"` | Cell and header alignment. |
| `visible` | `True` | `True` or `False` | Whether the column is rendered and searched. |
| `sortable` | `True` | `True` or `False` | Whether header clicks sort this column. |
| `formatter` | `None` | Callable `(value, row) -> str` | Custom display text before built-in type formatting. |
| `metadata` | `{}` | Mapping | App-specific metadata stored with the column. |

Common `Column` builder methods also work with every type: `.title(...)`, `.width(...)`, `.align(...)`, `.hide()`, `.no_sort()`, `.fmt(...)`, and `.metadata(...)`.

### Text

Text is the default column type. It displays the row value as text.

```python
import customtkinter as ctk

from CTkDataTable import CTkDataTable


app = ctk.CTk()
app.title("Text Column")
app.geometry("520x260")
app.grid_columnconfigure(0, weight=1)
app.grid_rowconfigure(0, weight=1)

columns = [
    {"key": "customer", "title": "Customer", "width": 260, "type": "text"},
]

rows = [
    {"customer": "Northwind Components"},
    {"customer": "Meridian Foods"},
]

table = CTkDataTable(app, columns=columns, data=rows)
table.grid(row=0, column=0, sticky="nsew", padx=16, pady=16)

app.mainloop()
```

Builder methods for text columns:

| Method | Parameters | What it sets |
| --- | --- | --- |
| `Column("customer").text()` | None | Sets `type="text"`. |
| `Column("customer").fmt(func)` | Callable `(value, row) -> str` | Sets a custom formatter for displayed text. |

Adjustable options for text columns:

| Option | Default | Accepted values | What it changes |
| --- | --- | --- | --- |
| Common options | See common options table | See common options table | Key, title, width, alignment, visibility, sorting, formatting, and metadata. |
| `type` | `"text"` | `"text"` | Uses plain text display. |

### Number

Number columns right-align by default and sort numerically.

```python
import customtkinter as ctk

from CTkDataTable import CTkDataTable


app = ctk.CTk()
app.title("Number Column")
app.geometry("520x260")
app.grid_columnconfigure(0, weight=1)
app.grid_rowconfigure(0, weight=1)

columns = [
    {
        "key": "quantity",
        "title": "Quantity",
        "width": 140,
        "type": "number",
        "number_format": "{:,.0f}",
    },
]

rows = [
    {"quantity": 12400},
    {"quantity": 820},
]

table = CTkDataTable(app, columns=columns, data=rows)
table.grid(row=0, column=0, sticky="nsew", padx=16, pady=16)

app.mainloop()
```

Builder methods for number columns:

| Method | Parameters | What it sets |
| --- | --- | --- |
| `Column("quantity").number(format=None)` | Optional format string or callable `(value) -> str` | Sets `type="number"` and optional `number_format`. |

Adjustable options for number columns:

| Option | Default | Accepted values | What it changes |
| --- | --- | --- | --- |
| Common options | See common options table | See common options table | Key, title, width, alignment, visibility, sorting, formatting, and metadata. |
| `type` | `"text"` | `"number"` | Uses numeric display and numeric sorting. |
| `align` | `"right"` | `"left"`, `"center"`, or `"right"` | Alignment. Number columns default to right alignment. |
| `number_format` | `None` | Format string using `.format(number)` or callable `(value) -> str` | Display format for numeric values. |

### Percentage

Percentage columns right-align by default, sort numerically, and format numeric row values with a percent sign.

```python
import customtkinter as ctk

from CTkDataTable import CTkDataTable


app = ctk.CTk()
app.title("Percentage Column")
app.geometry("540x260")
app.grid_columnconfigure(0, weight=1)
app.grid_rowconfigure(0, weight=1)

columns = [
    {
        "key": "margin",
        "title": "Margin",
        "width": 150,
        "type": "percentage",
        "percentage_format": "{value:.1f}%",
    },
]

rows = [
    {"margin": 18.4},
    {"margin": 7.5},
]

table = CTkDataTable(app, columns=columns, data=rows)
table.grid(row=0, column=0, sticky="nsew", padx=16, pady=16)

app.mainloop()
```

For ratio values such as `0.184`, set `percentage_multiplier` to `100` before display.

Builder methods for percentage columns:

| Method | Parameters | What it sets |
| --- | --- | --- |
| `Column("margin").percentage(format="{value:.0f}%", multiplier=1.0)` | Keyword-only format string and display multiplier | Sets `type="percentage"`, `percentage_format`, and `percentage_multiplier`. |

Adjustable options for percentage columns:

| Option | Default | Accepted values | What it changes |
| --- | --- | --- | --- |
| Common options | See common options table | See common options table | Key, title, width, alignment, visibility, sorting, formatting, and metadata. |
| `type` | `"text"` | `"percentage"` | Uses percentage display and numeric sorting. |
| `align` | `"right"` | `"left"`, `"center"`, or `"right"` | Alignment. Percentage columns default to right alignment. |
| `percentage_format` | `"{value:.0f}%"` | Format string using `value`, `raw_value`, and `multiplier`; positional `{}` also receives the display value. | Display format for percentage values. |
| `percentage_multiplier` | `1.0` | Number greater than `0` | Multiplies the raw numeric value before formatting. |

### Currency

Currency columns sort numerically and format money values.

```python
import customtkinter as ctk

from CTkDataTable import CTkDataTable


app = ctk.CTk()
app.title("Currency Column")
app.geometry("560x260")
app.grid_columnconfigure(0, weight=1)
app.grid_rowconfigure(0, weight=1)

columns = [
    {
        "key": "amount",
        "title": "Amount",
        "width": 150,
        "type": "currency",
        "currency_symbol": "GBP ",
        "currency_format": "{symbol}{value:,.2f}",
        "currency_negative_format": "({symbol}{value:,.2f})",
    },
]

rows = [
    {"amount": 12640.5},
    {"amount": -2450.75},
]

table = CTkDataTable(app, columns=columns, data=rows)
table.grid(row=0, column=0, sticky="nsew", padx=16, pady=16)

app.mainloop()
```

Builder methods for currency columns:

| Method | Parameters | What it sets |
| --- | --- | --- |
| `Column("amount").currency(symbol="$", format="{symbol}{value:,.2f}", negative_format="-{symbol}{value:,.2f}")` | Keyword-only formatting options | Sets `type="currency"` and currency formatting. |

Adjustable options for currency columns:

| Option | Default | Accepted values | What it changes |
| --- | --- | --- | --- |
| Common options | See common options table | See common options table | Key, title, width, alignment, visibility, sorting, formatting, and metadata. |
| `type` | `"text"` | `"currency"` | Uses currency display and numeric sorting. |
| `align` | `"right"` | `"left"`, `"center"`, or `"right"` | Alignment. Currency columns default to right alignment. |
| `currency_symbol` | `"$"` | String | Symbol or prefix used by currency format strings. |
| `currency_format` | `"{symbol}{value:,.2f}"` | Format string using `symbol`, `value`, and `signed_value` | Format for zero and positive values. |
| `currency_negative_format` | `"-{symbol}{value:,.2f}"` | Format string using `symbol`, absolute `value`, and `signed_value` | Format for negative values. |

### Date

Date columns accept `datetime.date`, `datetime.datetime`, and ISO date strings.

```python
from datetime import date

import customtkinter as ctk

from CTkDataTable import CTkDataTable


app = ctk.CTk()
app.title("Date Column")
app.geometry("560x260")
app.grid_columnconfigure(0, weight=1)
app.grid_rowconfigure(0, weight=1)

columns = [
    {"key": "due", "title": "Due", "width": 150, "type": "date", "date_format": "%d %b %Y"},
]

rows = [
    {"due": date(2026, 6, 12)},
    {"due": "2026-06-18"},
]

table = CTkDataTable(app, columns=columns, data=rows)
table.grid(row=0, column=0, sticky="nsew", padx=16, pady=16)

app.mainloop()
```

Builder methods for date columns:

| Method | Parameters | What it sets |
| --- | --- | --- |
| `Column("due").date(fmt="%Y-%m-%d")` | `strftime` format string | Sets `type="date"` and `date_format`. |

Adjustable options for date columns:

| Option | Default | Accepted values | What it changes |
| --- | --- | --- | --- |
| Common options | See common options table | See common options table | Key, title, width, alignment, visibility, sorting, formatting, and metadata. |
| `type` | `"text"` | `"date"` | Uses date display and date-aware sorting. |
| `date_format` | `"%Y-%m-%d"` | `strftime` format string | Display format for parsed date values. |

### Datetime

Datetime columns accept `datetime.datetime`, `datetime.date`, and ISO datetime strings.

```python
from datetime import datetime

import customtkinter as ctk

from CTkDataTable import CTkDataTable


app = ctk.CTk()
app.title("Datetime Column")
app.geometry("600x260")
app.grid_columnconfigure(0, weight=1)
app.grid_rowconfigure(0, weight=1)

columns = [
    {
        "key": "updated",
        "title": "Updated",
        "width": 180,
        "type": "datetime",
        "datetime_format": "%d %b %H:%M",
    },
]

rows = [
    {"updated": datetime(2026, 6, 4, 15, 45)},
    {"updated": "2026-06-05T09:15:00"},
]

table = CTkDataTable(app, columns=columns, data=rows)
table.grid(row=0, column=0, sticky="nsew", padx=16, pady=16)

app.mainloop()
```

Builder methods for datetime columns:

| Method | Parameters | What it sets |
| --- | --- | --- |
| `Column("updated").datetime(fmt="%Y-%m-%d %H:%M")` | `strftime` format string | Sets `type="datetime"` and `datetime_format`. |

Adjustable options for datetime columns:

| Option | Default | Accepted values | What it changes |
| --- | --- | --- | --- |
| Common options | See common options table | See common options table | Key, title, width, alignment, visibility, sorting, formatting, and metadata. |
| `type` | `"text"` | `"datetime"` | Uses datetime display and datetime-aware sorting. |
| `datetime_format` | `"%Y-%m-%d %H:%M"` | `strftime` format string | Display format for parsed datetime values. |

### Badge

Badge columns draw a rounded label for status-like values.

```python
import customtkinter as ctk

from CTkDataTable import CTkDataTable


app = ctk.CTk()
app.title("Badge Column")
app.geometry("560x260")
app.grid_columnconfigure(0, weight=1)
app.grid_rowconfigure(0, weight=1)

columns = [
    {
        "key": "status",
        "title": "Status",
        "width": 150,
        "type": "badge",
        "badge_colors": {"Open": "#22c55e", "Closed": "#64748b", "Blocked": "#ef4444"},
        "badge_fallback_color": "#94a3b8",
    },
]

rows = [
    {"status": "Open"},
    {"status": "Blocked"},
]

table = CTkDataTable(app, columns=columns, data=rows)
table.grid(row=0, column=0, sticky="nsew", padx=16, pady=16)

app.mainloop()
```

Builder methods for badge columns:

| Method | Parameters | What it sets |
| --- | --- | --- |
| `Column("status").badge(colors=None, fallback_color=None, fallback_handler=None)` | Optional color mapping, fallback color, and fallback handler | Sets `type="badge"` and badge styling options. |

Adjustable options for badge columns:

| Option | Default | Accepted values | What it changes |
| --- | --- | --- | --- |
| Common options | See common options table | See common options table | Key, title, width, alignment, visibility, sorting, formatting, and metadata. |
| `type` | `"text"` | `"badge"` | Draws the value as a rounded badge. |
| `badge_colors` | `{}` | Mapping of displayed text to color string or light/dark tuple | Fill color for known badge values. |
| `badge_fallback_color` | `None` | Color string or light/dark tuple | Fill color when the value is not in `badge_colors`. |
| `badge_fallback_handler` | `None` | Callable `(value, row, column) -> BadgeStyle, color, or None` | Dynamic fallback text and colors. |

### Checkbox

Checkbox columns display boolean row values and toggle them when clicked. The checked state is based on the truthiness of the row value. Toggle callbacks receive a `TableRowEvent` with the updated row, `column_key` set to the checkbox column, and `action_key` set to `"checkbox"`.

```python
import customtkinter as ctk

from CTkDataTable import CTkDataTable, TableRowEvent


app = ctk.CTk()
app.title("Checkbox Column")
app.geometry("560x260")
app.grid_columnconfigure(0, weight=1)
app.grid_rowconfigure(0, weight=1)

columns = [
    {"key": "approved", "title": "Approved", "width": 130, "type": "checkbox"},
]

rows = [
    {"approved": True},
    {"approved": False},
]


def handle_checkbox(event: TableRowEvent) -> None:
    approved = event.row[event.column_key]


table = CTkDataTable(
    app,
    columns=columns,
    data=rows,
    on_checkbox_toggle=handle_checkbox,
)
table.grid(row=0, column=0, sticky="nsew", padx=16, pady=16)

app.mainloop()
```

Builder methods for checkbox columns:

| Method | Parameters | What it sets |
| --- | --- | --- |
| `Column("approved").checkbox()` | None | Sets `type="checkbox"`. |

Adjustable options for checkbox columns:

| Option | Default | Accepted values | What it changes |
| --- | --- | --- | --- |
| Common options | See common options table | See common options table | Key, title, width, alignment, visibility, sorting, formatting, and metadata. |
| `type` | `"text"` | `"checkbox"` | Draws a clickable checkbox. |
| `align` | `"center"` | `"left"`, `"center"`, or `"right"` | Alignment. Checkbox columns default to center alignment. |

### Progress

Progress columns draw a numeric value as a progress bar.

```python
import customtkinter as ctk

from CTkDataTable import CTkDataTable


app = ctk.CTk()
app.title("Progress Column")
app.geometry("620x260")
app.grid_columnconfigure(0, weight=1)
app.grid_rowconfigure(0, weight=1)

columns = [
    {
        "key": "completion",
        "title": "Complete",
        "width": 180,
        "type": "progress",
        "progress_min": 0,
        "progress_max": 100,
        "progress_color": "#2563eb",
        "progress_background_color": "#dbeafe",
        "progress_show_text": True,
        "progress_text_format": "{percent:.0f}%",
    },
]

rows = [
    {"completion": 72},
    {"completion": 35},
]

table = CTkDataTable(app, columns=columns, data=rows)
table.grid(row=0, column=0, sticky="nsew", padx=16, pady=16)

app.mainloop()
```

Builder methods for progress columns:

| Method | Parameters | What it sets |
| --- | --- | --- |
| `Column("completion").progress(minimum=0.0, maximum=100.0, color=None, background_color=None, show_text=True, text_format="{percent:.0f}%")` | Keyword-only progress settings | Sets `type="progress"` and progress bar options. |

Adjustable options for progress columns:

| Option | Default | Accepted values | What it changes |
| --- | --- | --- | --- |
| Common options | See common options table | See common options table | Key, title, width, alignment, visibility, sorting, formatting, and metadata. |
| `type` | `"text"` | `"progress"` | Draws a progress bar and sorts numerically. |
| `align` | `"center"` | `"left"`, `"center"`, or `"right"` | Alignment. Progress columns default to center alignment. |
| `progress_min` | `0.0` | Number less than `progress_max` | Minimum value for the bar. |
| `progress_max` | `100.0` | Number greater than `progress_min` | Maximum value for the bar. |
| `progress_color` | `None` | Color string or light/dark tuple | Progress fill color. |
| `progress_background_color` | `None` | Color string or light/dark tuple | Progress track color. |
| `progress_show_text` | `True` | `True` or `False` | Whether text is drawn over the bar. |
| `progress_text_format` | `"{percent:.0f}%"` | Format string using `value`, `minimum`, `maximum`, `min`, `max`, `percent`, and `ratio` | Progress text. |

### Link

Link columns draw underlined text. A click calls `on_link_click` with a `TableRowEvent`.

```python
import customtkinter as ctk

from CTkDataTable import CTkDataTable, TableRowEvent


app = ctk.CTk()
app.title("Link Column")
app.geometry("620x300")
app.grid_columnconfigure(0, weight=1)
app.grid_rowconfigure(1, weight=1)

message = ctk.CTkLabel(app, text="Click a profile link", anchor="w")
message.grid(row=0, column=0, sticky="ew", padx=16, pady=(16, 8))

columns = [
    {"key": "name", "title": "Customer", "width": 220},
    {"key": "profile", "title": "Profile", "width": 140, "type": "link", "link_color": "#2563eb"},
]

rows = [
    {"name": "Northwind Components", "profile": "Open profile"},
    {"name": "Meridian Foods", "profile": "Open profile"},
]


def handle_link(event: TableRowEvent) -> None:
    message.configure(text=f"Link clicked for {event.row['name']}")


table = CTkDataTable(app, columns=columns, data=rows, on_link_click=handle_link)
table.grid(row=1, column=0, sticky="nsew", padx=16, pady=(0, 16))

app.mainloop()
```

Builder methods for link columns:

| Method | Parameters | What it sets |
| --- | --- | --- |
| `Column("profile").link(color=None)` | Optional color string or light/dark tuple | Sets `type="link"` and optional `link_color`. |

Adjustable options for link columns:

| Option | Default | Accepted values | What it changes |
| --- | --- | --- | --- |
| Common options | See common options table | See common options table | Key, title, width, alignment, visibility, sorting, formatting, and metadata. |
| `type` | `"text"` | `"link"` | Draws clickable underlined text. |
| `link_color` | `None` | Color string or light/dark tuple | Link text and underline color. |

### Pill List

Pill list columns display tags from a list, tuple, set, frozenset, comma-separated string, or single value.

```python
import customtkinter as ctk

from CTkDataTable import CTkDataTable


app = ctk.CTk()
app.title("Pill List Column")
app.geometry("640x260")
app.grid_columnconfigure(0, weight=1)
app.grid_rowconfigure(0, weight=1)

columns = [
    {
        "key": "tags",
        "title": "Tags",
        "width": 240,
        "type": "pill_list",
        "pill_colors": {"Urgent": "#ef4444", "Finance": "#0ea5e9"},
        "pill_fallback_color": "#64748b",
        "pill_text_color": "#ffffff",
    },
]

rows = [
    {"tags": ["Urgent", "Finance"]},
    {"tags": "Sales, Follow-up"},
]

table = CTkDataTable(app, columns=columns, data=rows)
table.grid(row=0, column=0, sticky="nsew", padx=16, pady=16)

app.mainloop()
```

Builder methods for pill list columns:

| Method | Parameters | What it sets |
| --- | --- | --- |
| `Column("tags").pill_list(colors=None, fallback_color=None, text_color=None)` | Optional color mapping, fallback color, and text color | Sets `type="pill_list"` and pill styling options. |

Adjustable options for pill list columns:

| Option | Default | Accepted values | What it changes |
| --- | --- | --- | --- |
| Common options | See common options table | See common options table | Key, title, width, alignment, visibility, sorting, formatting, and metadata. |
| `type` | `"text"` | `"pill_list"` | Draws values as compact tag pills. |
| `pill_colors` | `{}` | Mapping of pill text to color string or light/dark tuple | Fill color for known pill values. |
| `pill_fallback_color` | `None` | Color string or light/dark tuple | Fill color for pill values not found in `pill_colors`. |
| `pill_text_color` | `None` | Color string or light/dark tuple | Text color for every pill in the column. |

### Action

Action columns draw row-level buttons. A click calls `on_action_click` with `event.action_key`.

```python
import customtkinter as ctk

from CTkDataTable import CTkDataTable, TableRowEvent


app = ctk.CTk()
app.title("Action Column")
app.geometry("720x300")
app.grid_columnconfigure(0, weight=1)
app.grid_rowconfigure(1, weight=1)

message = ctk.CTkLabel(app, text="Click an action", anchor="w")
message.grid(row=0, column=0, sticky="ew", padx=16, pady=(16, 8))

columns = [
    {"key": "id", "title": "ID", "width": 80, "type": "number"},
    {"key": "name", "title": "Customer", "width": 220},
    {
        "key": "actions",
        "title": "Actions",
        "width": 180,
        "type": "action",
        "sortable": False,
        "actions": [
            {"key": "view", "label": "View"},
            {"key": "delete", "label": "Delete", "fg_color": "#fee2e2", "text_color": "#991b1b"},
        ],
    },
]

rows = [
    {"id": 1, "name": "Northwind Components", "actions": None},
    {"id": 2, "name": "Meridian Foods", "actions": None},
]


def handle_action(event: TableRowEvent) -> None:
    message.configure(text=f"{event.action_key} clicked for {event.row['name']}")


table = CTkDataTable(app, columns=columns, data=rows, on_action_click=handle_action)
table.grid(row=1, column=0, sticky="nsew", padx=16, pady=(0, 16))

app.mainloop()
```

Builder methods for action columns:

| Method | Parameters | What it sets |
| --- | --- | --- |
| `Column("actions").action(buttons, sortable=False)` | Sequence of action strings, dictionaries, or `TableAction` objects | Sets `type="action"`, `actions`, and `sortable`. |

Adjustable options for action columns:

| Option | Default | Accepted values | What it changes |
| --- | --- | --- | --- |
| Common options | See common options table | See common options table | Key, title, width, alignment, visibility, sorting, formatting, and metadata. |
| `type` | `"text"` | `"action"` | Draws row-level action buttons. |
| `align` | `"center"` | `"left"`, `"center"`, or `"right"` | Alignment. Action columns default to center alignment. |
| `sortable` | `True` for dictionary columns; `False` from `Column(...).action()` unless changed | `True` or `False` | Whether header clicks sort this action column. Usually set to `False`. |
| `actions` | `()` | Sequence of `TableAction`, mapping, or string actions | Buttons drawn in each row. |

## Major Features

### Built-In Search Entry

Set `searchable=True` to add a search entry above the table. Use `search_delay_ms` to debounce typing.

```python
table = CTkDataTable(
    app,
    columns=columns,
    data=rows,
    searchable=True,
    search_delay_ms=150,
    on_search=lambda query: None,
)
table.grid(row=0, column=0, sticky="nsew")
```

Searching is case-insensitive. It checks visible, non-action columns.

### External Search Entry

Use an external `CTkEntry` when you want the search box in your own toolbar.

```python
search = ctk.CTkEntry(app, placeholder_text="Search customers")
search.grid(row=0, column=0, sticky="ew")

table = CTkDataTable(app, columns=columns, data=rows)
table.grid(row=1, column=0, sticky="nsew")

search.bind("<KeyRelease>", lambda _event: table.search(search.get()))
```

### Sorting

Header clicks sort sortable columns. Clicking the same header again toggles direction. Use `sort_by()` from code when your app decides the sort order.

```python
def report_sort(column_key: str, ascending: bool) -> None:
    sort_state = (column_key, ascending)


table = CTkDataTable(app, columns=columns, data=rows, on_sort=report_sort)
table.sort_by("amount", ascending=False)
```

Missing values sort last. `number`, `percentage`, `currency`, and `progress` columns sort numerically. `date` and `datetime` columns sort by parsed date values. `checkbox` columns sort by boolean value. Other columns sort case-insensitively as text.

### Column Filters

Column filters combine with global search. A filtered column shows a header indicator.

```python
table.set_column_filter("status", {"type": "equals", "value": "Open"})
table.set_column_filter("amount", {"type": "range", "min": 100, "max": 500})
table.set_column_filter("due", {"type": "date_range", "min": "2026-06-01", "max": "2026-06-30"})

active_filters = table.get_column_filters()

table.clear_column_filter("status")
table.clear_column_filters()
```

Supported mapping filter definitions:

| Type | Definition | Match behavior |
| --- | --- | --- |
| `contains` | `{"type": "contains", "value": "north"}` | Case-insensitive substring match. |
| `equals` | `{"type": "equals", "value": "Open"}` | Exact Python equality. |
| `not_equals` | `{"type": "not_equals", "value": "Closed"}` | Exact Python inequality. |
| `in` | `{"type": "in", "values": ["Open", "Paused"]}` | Value is in a non-string iterable. |
| `bool` | `{"type": "bool", "value": True}` | `bool(value)` matches the expected boolean. |
| `range` | `{"type": "range", "min": 100, "max": 500}` | Numeric value is within optional min and max bounds. |
| `date_range` | `{"type": "date_range", "min": "2026-06-01", "max": "2026-06-30"}` | Parsed date or datetime is within optional bounds. |

You can also pass a callable:

```python
table.set_column_filter(
    "amount",
    lambda value, row: value is not None and float(value) >= 1000 and row["status"] == "Open",
)
```

### Selection and Multi-Select

Single selection is enabled by default. Set `multi_select=True` for Ctrl-click toggle selection and Shift-click range selection.

```python
table = CTkDataTable(app, columns=columns, data=rows, multi_select=True)

selected_row = table.get_selected_row()
selected_rows = table.get_selected_rows()
source_indices = table.get_selected_indices()
view_indices = table.get_selected_view_indices()
```

Keyboard navigation works when the table canvas has focus:

| Key | Behavior |
| --- | --- |
| Up, Down | Move one row. |
| Page Up, Page Down | Move by one page. |
| Home, End | Move to first or last visible row. |
| Enter | Calls `on_row_double_click` for the focused row. |
| Shift with movement | Extends the selection range in multi-select mode. |

### Bulk Actions with Multi-Select

```python
def delete_selected() -> None:
    removed = table.delete_selected_rows()
    deleted_count = removed


button = ctk.CTkButton(app, text="Delete selected", command=delete_selected)
button.grid(row=0, column=0, sticky="w")

table = CTkDataTable(app, columns=columns, data=rows, multi_select=True)
table.grid(row=1, column=0, sticky="nsew")
```

### Row, Cell, Link, Action, and Checkbox Callbacks

Interaction callbacks receive `TableRowEvent` for row-aware events. Action clicks do not also fire row or cell callbacks. Link clicks fire `on_link_click` when that callback is set. Checkbox clicks toggle the row value and fire `on_checkbox_toggle` when that callback is set.

```python
from CTkDataTable import TableRowEvent


def row_clicked(event: TableRowEvent) -> None:
    row_identity = (event.source_index, event.view_index)


def cell_clicked(event: TableRowEvent) -> None:
    selected_column = event.column_key


def action_clicked(event: TableRowEvent) -> None:
    selected_action = event.action_key


def checkbox_toggled(event: TableRowEvent) -> None:
    checked = event.row[event.column_key]


table = CTkDataTable(
    app,
    columns=columns,
    data=rows,
    on_row_click=row_clicked,
    on_cell_click=cell_clicked,
    on_action_click=action_clicked,
    on_checkbox_toggle=checkbox_toggled,
)
```

### Context Menus

Pass `context_menu` to show right-click row actions. On macOS or single-button setups, Control-click is also bound.

```python
from CTkDataTable import TableRowEvent


def handle_context(event: TableRowEvent) -> None:
    if event.action_key == "copy_id":
        app.clipboard_clear()
        app.clipboard_append(str(event.row["id"]))


table = CTkDataTable(
    app,
    columns=columns,
    data=rows,
    context_menu=[
        {"key": "copy_id", "label": "Copy ID"},
        {"key": "view", "label": "View"},
        "archive",
    ],
    on_context_action=handle_context,
)
```

### Resizable Columns and Horizontal Scroll

Set `resizable_columns=True` to let users drag header dividers. Set `horizontal_scroll=True` when the total column width is wider than the table.

```python
table = CTkDataTable(
    app,
    columns=columns,
    data=rows,
    resizable_columns=True,
    min_column_width=64,
    horizontal_scroll=True,
)

table.set_column_width("name", 260)
name_width = table.get_column_width("name")
```

When horizontal scrolling is enabled, Shift plus mouse wheel scrolls horizontally.

### Table Styling

Use `style` for table-wide colors, spacing, and corner radii. Pass a dictionary or a `TableStyle` object when creating the table. Later, call `configure_style()` to merge changes into the current style, or `set_style()` to replace it.

```python
from CTkDataTable import CTkDataTable, TableStyle


table = CTkDataTable(
    app,
    columns=columns,
    data=rows,
    style={
        "surface_bg": "#ffffff",
        "header_bg": "#111827",
        "header_text_color": "#ffffff",
        "row_alt_bg": "#f8fafc",
        "hover_bg": "#e0f2fe",
        "selected_bg": "#2563eb",
        "selected_text_color": "#ffffff",
        "divider_color": "#dbe3ef",
        "border_color": "#cbd5e1",
        "corner_radius": 12,
        "cell_padding_x": 14,
        "badge_radius": 7,
        "checkbox_radius": 4,
        "action_radius": 6,
    },
)

table.configure_style(
    link_text_color="#0f766e",
    checkbox_fill_checked="#16a34a",
    action_bg="#eff6ff",
)

table.set_style(
    TableStyle(
        surface_bg=("#ffffff", "#111827"),
        text_color=("#111827", "#e5e7eb"),
        header_bg=("#f1f5f9", "#020617"),
    )
)
```

Color options accept normal color strings or CustomTkinter light/dark tuples. Dimension options must be non-negative numbers. `style` also accepts aliases such as `fg_color`, `text`, `divider`, and `action_text`; the canonical option names are listed in the `TableStyle` reference.

### Style Hooks

Style hooks are opt-in. Set `enable_style_hooks=True`, then provide `row_style` and/or `cell_style`.

Style callbacks return `None` or a mapping with:

| Key | Effect |
| --- | --- |
| `fg_color` | Row or cell background color. |
| `text_color` | Row or cell text color. |

Colors can be strings or CustomTkinter light/dark tuples.

```python
def row_style(row):
    if row["status"] == "Overdue":
        return {"fg_color": "#fff7ed", "text_color": "#9a3412"}
    return None


def cell_style(_row, column_key, value):
    if column_key == "amount" and value < 0:
        return {"text_color": "#dc2626"}
    return None


table = CTkDataTable(
    app,
    columns=columns,
    data=rows,
    enable_style_hooks=True,
    row_style=row_style,
    cell_style=cell_style,
)
```

### BadgeStyle for Dynamic Badges

Use `BadgeStyle` when a badge fallback handler needs to set custom text and colors.

```python
from typing import Any, Mapping

from CTkDataTable import BadgeStyle, TableColumn


def status_fallback(value: Any, _row: Mapping[str, Any], _column: TableColumn) -> BadgeStyle:
    text = str(value or "Unknown")
    return BadgeStyle(text=text, fill_color="#64748b", text_color="#ffffff")


columns = [
    {
        "key": "status",
        "title": "Status",
        "width": 140,
        "type": "badge",
        "badge_colors": {"Open": "#22c55e", "Closed": "#64748b"},
        "badge_fallback_handler": status_fallback,
    }
]
```

### Footer Summaries

Set `footer=True` and provide `summaries`. Summaries run against the current visible rows after search and column filters.

```python
table = CTkDataTable(
    app,
    columns=columns,
    data=rows,
    footer=True,
    footer_height=38,
    summaries={
        "id": "count",
        "amount": "sum",
        "status": lambda visible_rows: f"{len(visible_rows)} visible",
    },
)
```

Built-in summary names are `count`, `sum`, `avg`, `average`, `min`, and `max`. Unknown strings are displayed as literal footer text.

### Loading State

Use `set_loading(True)` before a reload that you schedule back into the Tkinter event loop.

```python
def reload_rows() -> None:
    table.set_loading(True)
    app.after(50, finish_reload)


def finish_reload() -> None:
    table.set_data(fetch_rows())
    table.set_loading(False)
```

### Async Loading

Use `load_async()` to run a row loader on a background thread. The widget sets its loading state, runs your function, then safely calls `set_data()` on the Tkinter thread.

```python
import time


def fetch_rows():
    time.sleep(1)
    return [
        {"id": 1, "name": "Northwind Components", "status": "Open"},
        {"id": 2, "name": "Meridian Foods", "status": "Closed"},
    ]


def loaded(rows):
    loaded_count = len(rows)


def failed(error):
    last_error = error


thread = table.load_async(
    fetch_rows,
    on_success=loaded,
    on_error=failed,
    clear_on_error=False,
)
```

`load_async()` returns the daemon `threading.Thread`.

### Error State

Use `set_error()` to show an error message without changing rows. Use `clear_error()` to return to the current data view.

```python
table.set_error("Could not refresh customer data")
table.clear_error()
```

## Constructor Reference

```python
CTkDataTable(
    master,
    columns,
    data=None,
    *,
    row_height=42,
    header_height=44,
    footer_height=38,
    font=None,
    header_font=None,
    horizontal_scroll=False,
    multi_select=False,
    searchable=False,
    search_delay_ms=0,
    resizable_columns=False,
    min_column_width=48,
    style=None,
    enable_style_hooks=False,
    row_style=None,
    cell_style=None,
    context_menu=None,
    on_context_action=None,
    footer=False,
    summaries=None,
    empty_message="No records to display",
    loading_message="Loading records...",
    error_message="Could not load records",
    on_row_click=None,
    on_row_double_click=None,
    on_cell_click=None,
    on_action_click=None,
    on_link_click=None,
    on_checkbox_toggle=None,
    on_sort=None,
    on_search=None,
    **frame_kwargs,
)
```

`CTkDataTable` inherits from `customtkinter.CTkFrame`. Visual keyword arguments such as `corner_radius`, `border_width`, `fg_color`, and `border_color` style the rounded table viewport. If omitted, the table sets `corner_radius=12` and `border_width=1`.

| Argument | Default | Accepted values | How to apply it |
| --- | --- | --- | --- |
| `master` | Required | Parent widget such as `CTk`, `CTkFrame`, or a tab/container. | First positional argument. |
| `columns` | Required | Sequence of dictionaries, `TableColumn`, or `Column` objects. | `CTkDataTable(app, columns=columns)`. |
| `data` | `None` | Iterable of row-like mapping objects. `None` becomes an empty table. | Pass at creation or call `set_data()`. |
| `row_height` | `42` | Integer pixels, at least `28`. | `row_height=48`. |
| `header_height` | `44` | Integer pixels, at least `32`. | `header_height=46`. |
| `footer_height` | `38` | Integer pixels, at least `28`. Used when `footer=True`. | `footer_height=40`. |
| `font` | `None` | Tkinter/CustomTkinter font object or tuple accepted by Canvas text items. | `font=("Segoe UI", 13)`. |
| `header_font` | `None` | Font object or tuple. Defaults to `font` when supplied, otherwise a bold table default. | `header_font=("Segoe UI", 13, "bold")`. |
| `horizontal_scroll` | `False` | `True` or `False`. | `horizontal_scroll=True`. |
| `multi_select` | `False` | `True` or `False`. | `multi_select=True`. |
| `searchable` | `False` | `True` or `False`. | `searchable=True`. |
| `search_delay_ms` | `0` | Integer milliseconds, `0` or greater. | `search_delay_ms=150`. |
| `resizable_columns` | `False` | `True` or `False`. | `resizable_columns=True`. |
| `min_column_width` | `48` | Integer pixels, at least `24`. | `min_column_width=64`. |
| `style` | `None` | `TableStyle`, mapping, or `None`. Controls table-wide colors, spacing, and radii. | `style={"header_bg": "#111827"}`. |
| `enable_style_hooks` | `False` | `True` or `False`. Required for `row_style` and `cell_style`. | `enable_style_hooks=True`. |
| `row_style` | `None` | Callable `(row) -> mapping or None`. Supports `fg_color` and `text_color`. | `row_style=my_row_style`. |
| `cell_style` | `None` | Callable `(row, column_key, value) -> mapping or None`. Supports `fg_color` and `text_color`. | `cell_style=my_cell_style`. |
| `context_menu` | `None` | Sequence of `TableAction`, mapping, or string actions. | `context_menu=[{"key": "copy", "label": "Copy"}]`. |
| `on_context_action` | `None` | Callable `(event: TableRowEvent) -> None`. | `on_context_action=handle_context`. |
| `footer` | `False` | `True` or `False`. | `footer=True`. |
| `summaries` | `None` | Mapping of column key to summary name or callback. | `summaries={"amount": "sum"}`. |
| `empty_message` | `"No records to display"` | String. | `empty_message="No customers yet"`. |
| `loading_message` | `"Loading records..."` | String. | `loading_message="Loading customers..."`. |
| `error_message` | `"Could not load records"` | String. Used by `set_error(None)` and `load_async()` failures. | `error_message="Load failed"`. |
| `on_row_click` | `None` | Callable `(event: TableRowEvent) -> None`. | `on_row_click=select_row`. |
| `on_row_double_click` | `None` | Callable `(event: TableRowEvent) -> None`. Also called by Enter. | `on_row_double_click=open_row`. |
| `on_cell_click` | `None` | Callable `(event: TableRowEvent) -> None`. | `on_cell_click=inspect_cell`. |
| `on_action_click` | `None` | Callable `(event: TableRowEvent) -> None`. | `on_action_click=handle_action`. |
| `on_link_click` | `None` | Callable `(event: TableRowEvent) -> None`. | `on_link_click=open_link`. |
| `on_checkbox_toggle` | `None` | Callable `(event: TableRowEvent) -> None`. Fires after a checkbox cell toggles. | `on_checkbox_toggle=handle_checkbox`. |
| `on_sort` | `None` | Callable `(column_key: str, ascending: bool) -> None`. | `on_sort=report_sort`. |
| `on_search` | `None` | Callable `(query: str) -> None`. | `on_search=report_search`. |
| `**frame_kwargs` | Frame defaults plus table defaults | CustomTkinter `CTkFrame` options such as `fg_color`, `border_color`, `corner_radius`, `border_width`. | `fg_color=("white", "#1f2937")`. |

## TableStyle Reference

Use `TableStyle` or a style dictionary to customize the whole table. Any option left as `None` falls back to the active CustomTkinter theme and table defaults.

| Group | Options | Effect |
| --- | --- | --- |
| Shape and spacing | `corner_radius`, `border_width`, `cell_padding_x`, `badge_padding_x`, `button_padding_x`, `badge_radius`, `checkbox_radius`, `progress_radius`, `pill_radius`, `action_radius` | Table frame shape, cell padding, and feature-cell radii. |
| Main backgrounds | `canvas_bg`, `surface_bg`, `row_bg`, `row_alt_bg`, `header_bg`, `footer_bg`, `hover_bg`, `selected_bg`, `selected_hover_bg` | The canvas, table surface, row states, header, footer, hover, and selection backgrounds. |
| Text colors | `text_color`, `hover_text_color`, `selected_text_color`, `selected_hover_text_color`, `muted_text_color`, `header_text_color`, `footer_text_color` | Default, state, header, footer, and muted text colors. |
| Lines and indicators | `divider_color`, `header_divider_color`, `border_color`, `sort_indicator_color`, `filter_indicator_color`, `loading_indicator_color` | Row/header dividers, table border, sort/filter marks, and loading indicator. |
| Feature cells | `badge_bg`, `badge_text_color`, `pill_bg`, `pill_text_color`, `progress_bg`, `progress_fill`, `progress_text_color`, `link_text_color`, `checkbox_fill`, `checkbox_fill_checked`, `checkbox_border`, `checkbox_check`, `action_bg`, `action_border`, `action_text_color` | Default colors for badges, pills, progress bars, links, checkboxes, and action buttons. |

Supported alias names:

| Alias | Canonical option |
| --- | --- |
| `fg_color` | `canvas_bg` |
| `text`, `hover_text`, `selected_text`, `selected_hover_text`, `muted_text`, `header_text`, `footer_text` | Matching `*_color` option. |
| `divider`, `header_divider`, `table_border` | `divider_color`, `header_divider_color`, `border_color`. |
| `sort_indicator`, `filter_indicator`, `loading_indicator` | Matching `*_color` option. |
| `badge_default_bg`, `badge_text`, `pill_text`, `progress_text`, `link_text`, `action_text` | Matching feature-cell color option. |

## TableColumn Reference

Dictionary, `Column`, and `TableColumn` definitions normalize to `TableColumn`.

| Option | Default | Accepted values | How to apply it |
| --- | --- | --- | --- |
| `key` | Required | Unique string row field name. Must match row dictionary keys exactly. | `{"key": "name"}`. |
| `title` | Key title-cased for dictionaries and `Column`; required for direct `TableColumn`. | String header label. | `{"title": "Customer"}`. |
| `width` | `140` for dictionaries and `Column`; required for direct `TableColumn`. | Integer pixels greater than `0`. | `{"width": 220}`. |
| `align` | Depends on `type`. | `"left"`, `"center"`, or `"right"`. | `{"align": "right"}`. |
| `visible` | `True` | `True` or `False`. Hidden columns are not rendered or searched. | `{"visible": False}`. |
| `sortable` | `True` | `True` or `False`. Controls header-click sorting. | `{"sortable": False}`. |
| `type` | `"text"` | One of the 12 column types. | `{"type": "currency"}`. |
| `formatter` | `None` | Callable `(value, row) -> str`. Runs before type formatting. | `{"formatter": lambda value, row: str(value).upper()}`. |
| `number_format` | `None` | Format string using `.format(number)` or callable `(value) -> str`. | `{"number_format": "{:,.2f}"}`. |
| `percentage_format` | `"{value:.0f}%"` | Format string using `value`, `raw_value`, and `multiplier`; positional `{}` also receives the display value. | `{"percentage_format": "{value:.1f}%"}`. |
| `percentage_multiplier` | `1.0` | Number greater than `0`. | `{"percentage_multiplier": 100}`. |
| `currency_symbol` | `"$"` | String prefix or symbol. | `{"currency_symbol": "GBP "}`. |
| `currency_format` | `"{symbol}{value:,.2f}"` | Format string using `symbol`, `value`, and `signed_value`. | `{"currency_format": "{symbol}{value:,.0f}"}`. |
| `currency_negative_format` | `"-{symbol}{value:,.2f}"` | Format string using absolute `value`, plus `symbol` and `signed_value`. | `{"currency_negative_format": "({symbol}{value:,.2f})"}`. |
| `date_format` | `"%Y-%m-%d"` | `strftime` format string. | `{"date_format": "%d %b %Y"}`. |
| `datetime_format` | `"%Y-%m-%d %H:%M"` | `strftime` format string. | `{"datetime_format": "%d %b %H:%M"}`. |
| `badge_colors` | `{}` | Mapping of displayed badge text to color string or light/dark tuple. | `{"badge_colors": {"Open": "#22c55e"}}`. |
| `badge_fallback_color` | `None` | Color string or light/dark tuple. | `{"badge_fallback_color": "#64748b"}`. |
| `badge_fallback_handler` | `None` | Callable `(value, row, column) -> BadgeStyle, color, or None`. | `{"badge_fallback_handler": status_fallback}`. |
| `pill_colors` | `{}` | Mapping of pill text to color string or light/dark tuple. | `{"pill_colors": {"Urgent": "#ef4444"}}`. |
| `pill_fallback_color` | `None` | Color string or light/dark tuple. | `{"pill_fallback_color": "#64748b"}`. |
| `pill_text_color` | `None` | Color string or light/dark tuple. | `{"pill_text_color": "#ffffff"}`. |
| `actions` | `()` | Sequence of `TableAction`, mapping, or string actions. | `{"actions": [{"key": "view", "label": "View"}]}`. |
| `progress_min` | `0.0` | Number. Must be less than `progress_max`. | `{"progress_min": 0}`. |
| `progress_max` | `100.0` | Number. Must be greater than `progress_min`. | `{"progress_max": 100}`. |
| `progress_color` | `None` | Color string or light/dark tuple. | `{"progress_color": "#2563eb"}`. |
| `progress_background_color` | `None` | Color string or light/dark tuple. | `{"progress_background_color": "#dbeafe"}`. |
| `progress_show_text` | `True` | `True` or `False`. | `{"progress_show_text": False}`. |
| `progress_text_format` | `"{percent:.0f}%"` | Format string using `value`, `minimum`, `maximum`, `min`, `max`, `percent`, and `ratio`. | `{"progress_text_format": "{value:.0f}/{maximum:.0f}"}`. |
| `link_color` | `None` | Color string or light/dark tuple. | `{"link_color": "#2563eb"}`. |
| `metadata` | `{}` | Mapping for your own app-specific data. Not rendered. | `{"metadata": {"source": "crm"}}`. |

Default alignment by column type:

| Type | Default alignment |
| --- | --- |
| `number`, `percentage`, `currency` | `right` |
| `checkbox`, `action`, `progress` | `center` |
| All other types | `left` |

## Column Builder Reference

`Column("key")` creates a mapping accepted anywhere a column dictionary is accepted.

| Method | Parameters | Effect |
| --- | --- | --- |
| `Column(key)` | `key: str` | Starts a text column with the given row key. |
| `.title(title)` | `title: str` | Sets header text. |
| `.width(pixels)` | `pixels: int` | Sets column width. |
| `.align(align)` | `"left"`, `"center"`, `"right"` | Sets alignment. |
| `.hide()` | None | Sets `visible=False`. |
| `.no_sort()` | None | Sets `sortable=False`. |
| `.fmt(func)` | Callable `(value, row) -> str` | Sets `formatter`. |
| `.metadata(**kwargs)` | Keyword values | Sets `metadata`. |
| `.text()` | None | Sets `type="text"`. |
| `.number(format=None)` | Format string or callable | Sets `type="number"` and optional `number_format`. |
| `.percentage(format="{value:.0f}%", multiplier=1.0)` | Keyword-only format string and display multiplier | Sets percentage options. |
| `.currency(symbol="$", format="{symbol}{value:,.2f}", negative_format="-{symbol}{value:,.2f}")` | Keyword-only formatting options | Sets currency options. |
| `.date(fmt="%Y-%m-%d")` | `strftime` format | Sets date options. |
| `.datetime(fmt="%Y-%m-%d %H:%M")` | `strftime` format | Sets datetime options. |
| `.badge(colors=None, fallback_color=None, fallback_handler=None)` | Badge settings | Sets badge options. |
| `.pill_list(colors=None, fallback_color=None, text_color=None)` | Pill settings | Sets pill-list options. |
| `.checkbox()` | None | Sets `type="checkbox"`. |
| `.progress(minimum=0.0, maximum=100.0, color=None, background_color=None, show_text=True, text_format="{percent:.0f}%")` | Progress settings | Sets progress options. |
| `.link(color=None)` | Optional color | Sets link options. |
| `.action(buttons, sortable=False)` | Sequence of actions | Sets action button options. |

## TableAction Reference

`TableAction` defines a button inside an `action` column or an item in `context_menu`.

```python
from CTkDataTable import TableAction


TableAction("view", "View")
TableAction("delete", "Delete", fg_color="#fee2e2", text_color="#991b1b")
```

Dictionary and string forms are accepted:

```python
{"key": "view", "label": "View", "width": 72}
"archive"
```

String actions use the string as `key` and title-case it for the label.

| Option | Default | Accepted values | How to apply it |
| --- | --- | --- | --- |
| `key` | Required | String action identifier. | `{"key": "view"}`. |
| `label` | `key.title()` for dictionaries and strings; required for direct `TableAction`. | Button/menu text. | `{"label": "View"}`. |
| `width` | `None` | Positive integer pixels. If omitted, the button is measured from the label. | `{"width": 76}`. |
| `fg_color` | `None` | Color string or light/dark tuple. | `{"fg_color": "#fee2e2"}`. |
| `text_color` | `None` | Color string or light/dark tuple. | `{"text_color": "#991b1b"}`. |
| `border_color` | `None` | Color string or light/dark tuple. | `{"border_color": "#fecaca"}`. |

## BadgeStyle Reference

Use `BadgeStyle` from a `badge_fallback_handler`.

```python
BadgeStyle(text="Unknown", fill_color="#64748b", text_color="#ffffff")
```

| Field | Default | Accepted values | Effect |
| --- | --- | --- | --- |
| `text` | Required | String. | Text drawn inside the badge. |
| `fill_color` | Required | Color string or light/dark tuple. | Badge fill color. |
| `text_color` | `None` | Color string, light/dark tuple, or `None`. | Badge text color. |

Fallback handler return values:

| Return value | Result |
| --- | --- |
| `BadgeStyle(...)` | Uses custom badge text, fill color, and optional text color. |
| Color string or tuple | Keeps the original cell text and uses the returned fill color. |
| `None` | Uses `badge_fallback_color`, then the table default if no fallback color exists. |

## TableRowEvent Reference

Interaction callbacks receive `TableRowEvent`.

| Attribute | Type | Meaning |
| --- | --- | --- |
| `row` | `dict[str, Any]` | Shallow copy of the row. |
| `source_index` | `int` | Index in the original source data list. |
| `view_index` | `int` | Index in the current filtered and sorted view. |
| `column_key` | `str or None` | Clicked column key for cell, link, and action events. |
| `action_key` | `str or None` | Clicked action key. Link events use `"link"` and checkbox events use `"checkbox"`. |

Use `source_index` when you want the original data position. Use `view_index` when you intentionally want the current visible order after search, filters, and sorting.

## Method Reference

| Method | Returns | Use |
| --- | --- | --- |
| `set_data(data)` | `None` | Replace all rows and clear selection. |
| `get_data()` | `list[dict]` | Get shallow copies of all source rows. |
| `get_columns()` | `tuple[TableColumn, ...]` | Get normalized column definitions. |
| `set_columns(columns)` | `None` | Replace columns while preserving compatible sort/filter/selection state. |
| `set_column_width(column_key, width)` | `None` | Set one column width, clamped to `min_column_width`. |
| `get_column_width(column_key)` | `int` | Read one column width. |
| `refresh()` | `None` | Redraw without changing rows or state. |
| `get_style()` | `TableStyle` | Return the current table-wide style options. |
| `set_style(style=None, **kwargs)` | `None` | Replace table-wide style options and redraw. |
| `configure_style(style=None, **kwargs)` | `None` | Merge table-wide style options into the current style and redraw. |
| `clear()` | `None` | Remove all rows. |
| `get_selected_row()` | `dict or None` | Get the first selected row. |
| `get_selected_rows()` | `list[dict]` | Get all selected rows. |
| `get_selected_indices()` | `list[int]` | Get selected source indices in current view order. |
| `get_selected_view_indices()` | `list[int]` | Get selected visible row indices. |
| `get_row(index)` | `dict` | Get a source row by source index. |
| `get_view_row(view_index)` | `dict` | Get a row by visible view index. |
| `source_index_for_view_index(view_index)` | `int` | Convert visible index to source index. |
| `view_index_for_source_index(source_index)` | `int or None` | Convert source index to visible index, or `None` if hidden by filters/search. |
| `find_row_index(column_key, value)` | `int or None` | Find the first source row where the column equals `value`. |
| `sort_by(column_key, ascending=True)` | `None` | Sort visible rows. |
| `search(query)` | `None` | Case-insensitive global search across visible, non-action columns. |
| `filter(query)` | `None` | Backward-compatible alias for `search(query)`. |
| `set_column_filter(column_key, definition)` | `None` | Add or replace one column filter. |
| `clear_column_filter(column_key)` | `None` | Clear one column filter. |
| `clear_column_filters()` | `None` | Clear all column filters. |
| `get_column_filters()` | `dict` | Get active column filters. |
| `add_row(row)` | `int` | Append one row and return its source index. |
| `add_rows(rows)` | `list[int]` | Append multiple rows and return their source indices. |
| `update_row(index, row)` | `None` | Replace a source row by source index. |
| `update_view_row(view_index, row)` | `None` | Replace a row by current visible index. |
| `update_row_where(column_key, value, new_row)` | `bool` | Replace the first source row matching `column_key == value`. |
| `delete_row(index)` | `None` | Delete a source row by source index. |
| `delete_view_row(view_index)` | `None` | Delete a row by current visible index. |
| `delete_row_where(column_key, value)` | `bool` | Delete the first source row matching `column_key == value`. |
| `delete_row_by_key(column_key, value)` | `bool` | Alias for `delete_row_where()`. |
| `delete_selected_rows()` | `int` | Delete selected source rows and return the number removed. |
| `set_loading(state)` | `None` | Show or hide loading state. |
| `set_error(message=None)` | `None` | Show error state. `None` uses `error_message`. |
| `clear_error()` | `None` | Hide error state without changing rows. |
| `load_async(fetch_rows, on_success=None, on_error=None, clear_on_error=False)` | `threading.Thread` | Load rows in a background thread and update the table on the Tkinter thread. |

### Data Method Examples

```python
table.set_data([
    {"id": 1, "name": "Alice", "status": "Open"},
    {"id": 2, "name": "Bob", "status": "Closed"},
])

rows = table.get_data()
table.clear()
```

```python
source_index = table.add_row({"id": 3, "name": "Diana", "status": "Open"})
source_indices = table.add_rows([
    {"id": 4, "name": "Evan", "status": "Open"},
    {"id": 5, "name": "Fatima", "status": "Closed"},
])
```

```python
table.update_row(0, {"id": 1, "name": "Alice Updated", "status": "Open"})
table.update_view_row(0, {"id": 2, "name": "Bob Updated", "status": "Closed"})

updated = table.update_row_where(
    "id",
    3,
    {"id": 3, "name": "Diana Updated", "status": "Open"},
)
```

```python
table.delete_row(0)
table.delete_view_row(0)

deleted = table.delete_row_where("id", 5)
deleted_again = table.delete_row_by_key("id", 4)
```

### Navigation and Selection Method Examples

```python
first_source_row = table.get_row(0)
first_visible_row = table.get_view_row(0)

source_index = table.source_index_for_view_index(0)
view_index = table.view_index_for_source_index(source_index)
found_index = table.find_row_index("id", 42)
```

```python
one_row = table.get_selected_row()
many_rows = table.get_selected_rows()
source_indices = table.get_selected_indices()
view_indices = table.get_selected_view_indices()
```

### Column Method Examples

```python
columns = table.get_columns()

table.set_columns([
    {"key": "id", "title": "ID", "width": 80, "type": "number"},
    {"key": "name", "title": "Customer", "width": 240},
])

table.set_column_width("name", 280)
current_width = table.get_column_width("name")
table.refresh()
```

### Style Method Examples

```python
current_style = table.get_style()

table.configure_style(
    header_bg="#111827",
    header_text_color="#ffffff",
    selected_bg="#2563eb",
)

table.set_style(
    {
        "surface_bg": "#ffffff",
        "row_bg": "#ffffff",
        "row_alt_bg": "#f8fafc",
        "text_color": "#111827",
    }
)
```

### Search, Sort, and Filter Method Examples

```python
table.sort_by("name", ascending=True)
table.search("north")
table.filter("north")

table.set_column_filter("status", {"type": "equals", "value": "Open"})
table.clear_column_filter("status")
table.clear_column_filters()
```

### Loading Method Examples

```python
table.set_loading(True)
table.set_data(fetch_rows())
table.set_loading(False)

table.set_error("Could not load rows")
table.clear_error()
```

```python
thread = table.load_async(
    fetch_rows,
    on_success=lambda rows: None,
    on_error=lambda error: None,
    clear_on_error=True,
)
```

## rows_from_cursor Reference

`rows_from_cursor(cursor)` converts a DB-API cursor result into dictionaries using `cursor.description`.

```python
from CTkDataTable import rows_from_cursor


cursor.execute("SELECT id, name, status FROM customers")
rows = rows_from_cursor(cursor)
table.set_data(rows)
```

| Parameter | Accepted values | Returns |
| --- | --- | --- |
| `cursor` | DB-API cursor after a `SELECT` query has executed and `cursor.description` is available. | `list[dict]` |

## Complete Mini App

This app combines search, sorting, badges, currency, dates, checkboxes, row actions, context menus, footer summaries, and multi-select.

```python
from datetime import date, timedelta

import customtkinter as ctk

from CTkDataTable import CTkDataTable, TableRowEvent


app = ctk.CTk()
app.title("Work Orders")
app.geometry("1080x620")
app.grid_columnconfigure(0, weight=1)
app.grid_rowconfigure(2, weight=1)

toolbar = ctk.CTkFrame(app, corner_radius=0)
toolbar.grid(row=0, column=0, sticky="ew", padx=14, pady=(14, 8))
toolbar.grid_columnconfigure(0, weight=1)

search = ctk.CTkEntry(toolbar, placeholder_text="Search work orders")
search.grid(row=0, column=0, sticky="ew", padx=(10, 8), pady=10)

detail = ctk.CTkLabel(app, text="No row selected", anchor="w")
detail.grid(row=1, column=0, sticky="ew", padx=14, pady=(0, 8))

today = date.today()
columns = [
    {"key": "id", "title": "WO", "width": 90},
    {"key": "title", "title": "Title", "width": 260},
    {
        "key": "priority",
        "title": "Priority",
        "width": 120,
        "type": "badge",
        "badge_colors": {"High": "#ef4444", "Medium": "#f59e0b", "Low": "#22c55e"},
        "badge_fallback_color": "#64748b",
    },
    {"key": "cost", "title": "Cost", "width": 110, "type": "currency"},
    {"key": "due", "title": "Due", "width": 125, "type": "date", "date_format": "%d %b"},
    {"key": "complete", "title": "Done", "width": 90, "type": "checkbox"},
    {
        "key": "actions",
        "title": "Actions",
        "width": 170,
        "type": "action",
        "sortable": False,
        "actions": [
            {"key": "view", "label": "View"},
            {"key": "delete", "label": "Delete"},
        ],
    },
]

rows = [
    {
        "id": "WO-001",
        "title": "Replace intake filter",
        "priority": "High",
        "cost": 450,
        "due": today + timedelta(days=2),
        "complete": False,
        "actions": None,
    },
    {
        "id": "WO-002",
        "title": "Update inspection checklist",
        "priority": "Low",
        "cost": 120,
        "due": today + timedelta(days=8),
        "complete": True,
        "actions": None,
    },
    {
        "id": "WO-003",
        "title": "Audit calibration records",
        "priority": "Medium",
        "cost": 275,
        "due": today + timedelta(days=4),
        "complete": False,
        "actions": None,
    },
]

table: CTkDataTable | None = None


def select_row(event: TableRowEvent) -> None:
    detail.configure(text=f"Selected {event.row['id']}: {event.row['title']}")


def handle_action(event: TableRowEvent) -> None:
    if table is None:
        return
    if event.action_key == "view":
        detail.configure(text=f"Viewing {event.row['id']}")
    elif event.action_key == "delete":
        table.delete_row_by_key("id", event.row["id"])


def handle_context(event: TableRowEvent) -> None:
    if event.action_key == "copy_id":
        app.clipboard_clear()
        app.clipboard_append(event.row["id"])
        detail.configure(text=f"Copied {event.row['id']}")


def handle_checkbox(event: TableRowEvent) -> None:
    detail.configure(
        text=f"{event.row['id']} complete: {event.row[event.column_key]}"
    )


table = CTkDataTable(
    app,
    columns=columns,
    data=rows,
    horizontal_scroll=True,
    multi_select=True,
    footer=True,
    summaries={"id": "count", "cost": "sum"},
    context_menu=[{"key": "copy_id", "label": "Copy ID"}],
    on_row_click=select_row,
    on_action_click=handle_action,
    on_context_action=handle_context,
    on_checkbox_toggle=handle_checkbox,
)
table.grid(row=2, column=0, sticky="nsew", padx=14, pady=(0, 14))

search.bind("<KeyRelease>", lambda _event: table.search(search.get()))

app.mainloop()
```

## Readiness Assessment

The consolidated documentation is ready for a mixed technical and non-technical audience. It leads with tasks, keeps the exact key-matching constraint visible early, covers static, live-update, and interactive use cases equally, and gives developers a complete reference for constructor options, column options, helper classes, events, filters, callbacks, and methods.
