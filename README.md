# CTkDataTable

The `CTkDataTable` package provides a virtualized data table widget for CustomTkinter apps.

Use it when you want to show records from Python data, PostgreSQL queries, SQLite queries, or SQLAlchemy results without building a grid of labels by hand.

## Install

From PyPI:

```powershell
pip install CTkDataTable
```

For local development:

```powershell
pip install -e ".[dev]"
```

## Run a Demo

```powershell
python -m CTkDataTable.examples.basic_table
python -m CTkDataTable.examples.ncr_records
```

## Development Checks

```powershell
python -m unittest discover -v
python -m ruff check .
python -m mypy CTkDataTable
python -m build
python -m twine check dist/*
```

## Release Build

```powershell
Remove-Item -Recurse -Force dist, build -ErrorAction SilentlyContinue
python -m build
python -m twine check dist/*
```

## License

MIT License. See [LICENSE](https://github.com/Harry-g25/CTkTableData/blob/main/LICENSE).

## Quick Start

Using the table has three steps:

1. Define the columns.
2. Pass rows.
3. Place the table in your CustomTkinter layout.

```python
import customtkinter as ctk

from CTkDataTable import CTkDataTable


app = ctk.CTk()
app.geometry("700x400")
app.grid_rowconfigure(0, weight=1)
app.grid_columnconfigure(0, weight=1)

columns = [
    {"key": "id", "title": "ID", "width": 80},
    {"key": "name", "title": "Name", "width": 180},
    {"key": "status", "title": "Status", "width": 140},
]

rows = [
    {"id": 1, "name": "Alice", "status": "Open"},
    {"id": 2, "name": "Bob", "status": "Closed"},
    {"id": 3, "name": "Charlie", "status": "In Review"},
]

table = CTkDataTable(app, columns=columns, data=rows)
table.grid(row=0, column=0, sticky="nsew", padx=16, pady=16)

app.mainloop()
```

The important rule is simple:

```python
column["key"] == row dictionary key
```

For example:

```python
{"key": "name", "title": "Name", "width": 180}
{"name": "Alice"}
```

## Loading Data

Most users can pass a list of dictionaries:

```python
table.set_data([
    {"id": 1, "name": "Alice", "status": "Open"},
    {"id": 2, "name": "Bob", "status": "Closed"},
])
```

The table also accepts common database row objects, including:

- PostgreSQL rows returned as dictionaries
- SQLAlchemy mapping rows
- `sqlite3.Row` objects
- plain DB-API tuple cursors converted with `rows_from_cursor()`

### PostgreSQL with psycopg 3

Use `dict_row`, then pass the query result directly to the table.

```python
import psycopg
from psycopg.rows import dict_row


with psycopg.connect(DB_URL, row_factory=dict_row) as connection:
    rows = connection.execute("""
        SELECT id, name, status
        FROM customers
    """).fetchall()

table.set_data(rows)
```

### PostgreSQL with psycopg2

Use `RealDictCursor`.

```python
import psycopg2
from psycopg2.extras import RealDictCursor


connection = psycopg2.connect(DB_URL)
cursor = connection.cursor(cursor_factory=RealDictCursor)

cursor.execute("""
    SELECT id, name, status
    FROM customers
""")

table.set_data(cursor.fetchall())
```

### Plain DB-API Cursors

If your cursor returns tuples, convert them with `rows_from_cursor()`.

```python
from CTkDataTable import rows_from_cursor


cursor.execute("""
    SELECT id, name, status
    FROM customers
""")

table.set_data(rows_from_cursor(cursor))
```

If database column names do not match your table column keys, use SQL aliases:

```sql
SELECT created_at AS created FROM customers;
```

## Column Types

Every column needs at least a `key`, `title`, and `width`.

```python
{"key": "name", "title": "Name", "width": 180}
```

You can also set a `type`.

### Text

```python
{"key": "name", "title": "Name", "width": 180, "type": "text"}
```

### Number

```python
{"key": "amount", "title": "Amount", "width": 120, "type": "number"}
```

Format numbers with `number_format`:

```python
{"key": "amount", "title": "Amount", "width": 120, "type": "number", "number_format": "${:,.2f}"}
```

### Percentage

Use `percentage` for percent values. It right-aligns by default, sorts numerically, and appends `%`.

```python
{"key": "margin", "title": "Margin", "width": 120, "type": "percentage"}
```

Customize output with `percentage_format`. If your row values are stored as ratios, multiply them before display:

```python
{
    "key": "margin",
    "title": "Margin",
    "width": 120,
    "type": "percentage",
    "percentage_format": "{value:.1f}%",
    "percentage_multiplier": 100,
}
```

### Currency

Use `currency` for money values. It right-aligns by default, sorts numerically, and formats numeric row values.

```python
{
    "key": "amount",
    "title": "Amount",
    "width": 120,
    "type": "currency",
    "currency_symbol": "$",
}
```

Customize output with `currency_format` and `currency_negative_format`:

```python
{
    "key": "amount",
    "title": "Amount",
    "width": 120,
    "type": "currency",
    "currency_symbol": "GBP ",
    "currency_format": "{symbol}{value:,.2f}",
    "currency_negative_format": "({symbol}{value:,.2f})",
}
```

### Date

```python
{"key": "created", "title": "Created", "width": 130, "type": "date"}
```

Date columns accept `datetime.date`, `datetime.datetime`, and ISO date strings.

### Badge

Use badges for status-like values.

```python
{
    "key": "status",
    "title": "Status",
    "width": 130,
    "type": "badge",
    "badge_colors": {
        "Open": "#2ecc71",
        "Closed": "#e74c3c",
        "Overdue": "#e67e22",
    },
    "badge_fallback_color": "#64748b",
}
```

### Pill List

Use `pill_list` for compact tag lists. Row values can be a list, tuple, set, or a comma-separated string.

```python
{
    "key": "tags",
    "title": "Tags",
    "width": 180,
    "type": "pill_list",
    "pill_colors": {"Urgent": "#ef4444", "Finance": "#0ea5e9"},
    "pill_fallback_color": "#64748b",
    "pill_text_color": "#ffffff",
}
```

### Checkbox

Checkbox columns display boolean row values and toggle them when clicked. Toggle callbacks receive a
`TableRowEvent` with the updated row, `column_key` set to the checkbox column, and `action_key` set to
`"checkbox"`.

```python
from CTkDataTable import TableRowEvent


def handle_checkbox(event: TableRowEvent) -> None:
    approved = event.row[event.column_key]


columns = [
    {"key": "approved", "title": "Approved", "width": 100, "type": "checkbox"},
]

table = CTkDataTable(app, columns=columns, data=rows, on_checkbox_toggle=handle_checkbox)
```

### Progress

Use `progress` for numeric completion values. Values are clamped between `progress_min` and `progress_max`.

```python
{
    "key": "completion",
    "title": "Complete",
    "width": 140,
    "type": "progress",
    "progress_min": 0,
    "progress_max": 100,
    "progress_text_format": "{percent:.0f}%",
}
```

### Link

Use `link` for clickable text cells. Link clicks fire `on_link_click` with a `TableRowEvent`.

```python
from CTkDataTable import TableRowEvent


def handle_link(event: TableRowEvent) -> None:
    selected_profile = event.row


columns = [
    {"key": "profile", "title": "Profile", "width": 130, "type": "link"},
]

table = CTkDataTable(app, columns=columns, data=rows, on_link_click=handle_link)
```

### Actions

Action columns draw buttons inside each row.

```python
from CTkDataTable import CTkDataTable, TableRowEvent


def handle_action(event: TableRowEvent) -> None:
    selected_action = event.action_key


columns = [
    {"key": "id", "title": "ID", "width": 80},
    {
        "key": "actions",
        "title": "Actions",
        "width": 160,
        "type": "action",
        "sortable": False,
        "actions": [
            {"key": "view", "label": "View"},
            {"key": "delete", "label": "Delete"},
        ],
    },
]

table = CTkDataTable(
    app,
    columns=columns,
    data=rows,
    on_action_click=handle_action,
)
```

## Common Tasks

### Replace All Rows

```python
table.set_data(rows)
```

### Add One Row

```python
table.add_row({"id": 4, "name": "Diana", "status": "Open"})
```

### Search from a Search Box

```python
search = ctk.CTkEntry(app, placeholder_text="Search")
search.grid(row=0, column=0, sticky="ew")

table.grid(row=1, column=0, sticky="nsew")

search.bind("<KeyRelease>", lambda _event: table.search(search.get()))
```

### Sort by a Column

```python
table.sort_by("name", ascending=True)
```

Users can also click sortable column headers.

### Resize Columns

```python
table = CTkDataTable(app, columns=columns, data=rows, resizable_columns=True)
```

Users can drag header dividers to resize columns. The table keeps the resize in memory for the current widget instance.

You can also change columns from code:

```python
table.set_column_width("name", 220)
table.set_columns([
    {"key": "id", "title": "ID", "width": 80},
    {"key": "name", "title": "Customer", "width": 220},
])
```

### Style the Table

Use `style` to control the table surface, header, rows, selection, dividers, feature cells, padding, and corner radii.
Pass either a dictionary or a `TableStyle` object.

```python
table = CTkDataTable(
    app,
    columns=columns,
    data=rows,
    style={
        "corner_radius": 12,
        "border_width": 1,
        "border_color": "#d1d5db",
        "header_bg": "#f3f4f6",
        "row_bg": "#ffffff",
        "row_alt_bg": "#f9fafb",
        "hover_bg": "#eef6ff",
        "selected_bg": "#2563eb",
        "selected_text_color": "#ffffff",
        "divider_color": "#e5e7eb",
        "badge_radius": 8,
        "action_radius": 6,
        "cell_padding_x": 14,
    },
)

table.configure_style(header_bg="#111827", header_text_color="#ffffff")
table.set_style(row_bg="#ffffff", row_alt_bg="#f8fafc")
```

### Style Rows and Cells

Style hooks are opt-in. Passing `row_style` or `cell_style` without `enable_style_hooks=True` raises a clear error.

```python
def row_style(row):
    if row["status"] == "Overdue":
        return {"fg_color": "#fff7ed", "text_color": "#9a3412"}
    return None


def cell_style(row, column_key, value):
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

### Filter by Column

Column filters combine with global search.

```python
table.set_column_filter("status", {"type": "equals", "value": "Open"})
table.set_column_filter("amount", {"type": "range", "min": 100, "max": 500})
table.clear_column_filter("status")
table.clear_column_filters()
```

Supported filter types are `contains`, `equals`, `not_equals`, `in`, `bool`, `range`, and `date_range`.

### Add a Context Menu

```python
def handle_context(event: TableRowEvent) -> None:
    selected_action = event.action_key


table = CTkDataTable(
    app,
    columns=columns,
    data=rows,
    context_menu=[
        {"key": "copy_id", "label": "Copy ID"},
        {"key": "delete", "label": "Delete"},
    ],
    on_context_action=handle_context,
)
```

### Show a Footer Summary

Footer summaries use the current visible rows after search and column filters.

```python
table = CTkDataTable(
    app,
    columns=columns,
    data=rows,
    footer=True,
    summaries={
        "id": "count",
        "amount": "sum",
        "status": lambda rows: f"{len(rows)} visible",
    },
)
```

Built-in summaries are `count`, `sum`, `avg`, `min`, and `max`.

### Load Rows in the Background

```python
def fetch_rows():
    return database.load_customers()


table.load_async(
    fetch_rows,
    on_success=lambda rows: None,
    on_error=lambda error: None,
)
```

`load_async()` shows the loading state, runs your fetch function in a background thread, and updates the table safely on the Tkinter thread.

### Get the Selected Row

```python
selected = table.get_selected_row()
if selected is not None:
    selected_id = selected.get("id")
```

For row identity, use source-data indices or current view indices:

```python
source_indices = table.get_selected_indices()
view_indices = table.get_selected_view_indices()
```

### Delete Rows

```python
table.delete_row(0)
table.delete_view_row(0)
table.delete_row_by_key("id", 4)
table.delete_selected_rows()
```

`delete_row(index)` uses the original source-data index. `delete_row_by_key()` is usually easier after sorting or filtering.
Use `delete_view_row(view_index)` when you intentionally want to target the current visible row order.

### Detailed Event Payloads

Interaction callbacks receive `TableRowEvent` objects when you need the row, source index, visible index, clicked column, or clicked action.

```python
def handle_action(event):
    row_identity = (event.source_index, event.view_index, event.action_key)


table = CTkDataTable(
    app,
    columns=columns,
    data=rows,
    on_action_click=handle_action,
)
```

For link cells, `event.column_key` is the link column and `event.action_key` is `"link"`.
For checkbox cells, `event.column_key` is the checkbox column, `event.action_key` is `"checkbox"`, and
`event.row[event.column_key]` is the new boolean value.

### Show a Loading State

```python
table.set_loading(True)
table.set_data(rows)
table.set_loading(False)
```

### Enable Horizontal Scrolling

Use this when the total column width is wider than the window.

```python
table = CTkDataTable(app, columns=columns, data=rows, horizontal_scroll=True)
```

### Keyboard Navigation

When the table has focus, use Up, Down, Page Up, Page Down, Home, and End to move selection. Press Enter to trigger the double-click row callback. In multi-select mode, Shift extends the selection range.

## Notes

- The table does not edit text, number, date, or badge cells inline. Checkbox columns can toggle boolean values.
- The table does not run database queries. Query your database yourself, then call `set_data()`.
- The table only draws visible rows, so large lists scroll smoothly.
- `delete_row(index)` deletes from the original data list, not the currently visible filtered or sorted row number.
- Searching clears selected rows that are no longer visible.
- Sorting and searching reset the vertical scroll position to the top.

## More Detail

- Full API reference: [docs/Docs.md](https://github.com/Harry-g25/CTkTableData/blob/main/docs/Docs.md)
- Standalone HTML guide: [docs/Docs.html](https://github.com/Harry-g25/CTkTableData/blob/main/docs/Docs.html)
- Basic example: [CTkDataTable/examples/basic_table.py](https://github.com/Harry-g25/CTkTableData/blob/main/CTkDataTable/examples/basic_table.py)
- NCR records example: [CTkDataTable/examples/ncr_records.py](https://github.com/Harry-g25/CTkTableData/blob/main/CTkDataTable/examples/ncr_records.py)
