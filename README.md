<div align="center">

<img src="https://capsule-render.vercel.app/api?type=rect&amp;height=180&amp;color=0:020617,50:111827,100:312e81&amp;text=CTkDataTable&amp;fontColor=ffffff&amp;fontSize=52&amp;fontAlignY=42&amp;desc=Modern%20data%20tables%20for%20CustomTkinter%20desktop%20apps&amp;descAlignY=68&amp;descSize=18" />

<br>

<p>
  <img src="https://readme-typing-svg.demolab.com?font=JetBrains+Mono&amp;weight=500&amp;size=20&amp;pause=1200&amp;color=A78BFA&amp;center=true&amp;vCenter=true&amp;width=760&amp;lines=Modern+tables+for+CustomTkinter;Built+for+desktop+apps+and+admin+tools;Display+structured+data+without+ttk.Treeview" />
</p>

<p>
  <a href="https://pypi.org/project/CTkDataTable/">
    <img src="https://img.shields.io/pypi/v/CTkDataTable?style=for-the-badge&amp;logo=pypi&amp;logoColor=white&amp;color=7c3aed" />
  </a>
  <a href="https://pypi.org/project/CTkDataTable/">
    <img src="https://img.shields.io/pypi/pyversions/CTkDataTable?style=for-the-badge&amp;logo=python&amp;logoColor=white&amp;color=2563eb" />
  </a>
  <img src="https://img.shields.io/badge/CustomTkinter-Compatible-111827?style=for-the-badge" />
  <img src="https://img.shields.io/badge/Status-In%20Development-a855f7?style=for-the-badge" />
</p>

</div>

---

## What is CTkDataTable?

`CTkDataTable` is a Python module for building cleaner, more practical data tables inside `customtkinter` desktop applications.

It was created to solve a common problem: CustomTkinter is great for modern desktop interfaces, but displaying structured table data can still be awkward. Standard Tkinter options such as `ttk.Treeview` often feel dated, difficult to style, or out of place in a modern UI.

`CTkDataTable` provides a configurable table widget designed for internal tools, dashboards, admin panels, database applications and workflow software.

---

## Preview

<div align="center">

<img src="assets/ctkdatatable-preview.png" alt="CTkDataTable Preview" width="850" />


---

## Why Use It?

<table>
  <tr>
    <td width="33%">
      <h3>CustomTkinter Friendly</h3>
      <p>Designed to fit naturally into modern CustomTkinter applications.</p>
    </td>
    <td width="33%">
      <h3>Dictionary Based</h3>
      <p>Define columns and rows using simple Python dictionaries.</p>
    </td>
    <td width="33%">
      <h3>Practical</h3>
      <p>Built for dashboards, admin tools, database viewers and internal systems.</p>
    </td>
  </tr>
</table>

---

## Features

* Built for `customtkinter`
* Simple column configuration
* Row data passed as dictionaries
* Configurable column titles
* Configurable column widths
* Text columns
* Number columns
* Badge columns
* Cleaner alternative to `ttk.Treeview`
* Useful for desktop dashboards and database-driven apps

---

## Installation

```bash
pip install CTkDataTable
```

---

## Quick Start

```python
import customtkinter as ctk
from CTkDataTable import CTkDataTable

app = ctk.CTk()
app.title("CTkDataTable Example")
app.geometry("900x500")

columns = [
    {
        "key": "id",
        "title": "ID",
        "width": 50,
        "type": "number"
    },
    {
        "key": "first_name",
        "title": "First Name",
        "width": 140,
        "type": "text"
    },
    {
        "key": "last_name",
        "title": "Last Name",
        "width": 140,
        "type": "text"
    },
    {
        "key": "position",
        "title": "Position",
        "width": 180,
        "type": "text"
    },
    {
        "key": "permission",
        "title": "Permission",
        "width": 140,
        "type": "badge",
        "badge_colors": {
            "Admin": "red",
            "Manager": "blue",
            "Standard": "gray"
        }
    }
]

rows = [
    {
        "id": 1,
        "first_name": "Harry",
        "last_name": "Gomm",
        "position": "Manager",
        "permission": "Manager"
    },
    {
        "id": 2,
        "first_name": "Ben",
        "last_name": "Jones",
        "position": "Engineer",
        "permission": "Standard"
    },
    {
        "id": 3,
        "first_name": "Charlie",
        "last_name": "Smith",
        "position": "Admin",
        "permission": "Admin"
    }
]

table = CTkDataTable(
    master=app,
    columns=columns,
    rows=rows
)

table.pack(fill="both", expand=True, padx=20, pady=20)

app.mainloop()
```

---

## How It Works

```mermaid
flowchart LR
    A[Define Columns] --> B[Create Row Data]
    B --> C[Pass Data to CTkDataTable]
    C --> D[Render Table]
    D --> E[Display Structured Data]
```

---

## Column Configuration

Columns are defined using dictionaries.

```python
columns = [
    {
        "key": "first_name",
        "title": "First Name",
        "width": 140,
        "type": "text"
    }
]
```

| Property | Description                              |
| -------- | ---------------------------------------- |
| `key`    | The key used to match data from each row |
| `title`  | The text displayed in the table header   |
| `width`  | The width of the column                  |
| `type`   | The column display type                  |

---

## Supported Column Types

<table>
  <tr>
    <td width="33%">
      <h3>Text</h3>
      <p>For names, labels, descriptions and general values.</p>
    </td>
    <td width="33%">
      <h3>Number</h3>
      <p>For IDs, counts, quantities and numeric data.</p>
    </td>
    <td width="33%">
      <h3>Badge</h3>
      <p>For statuses, permissions, categories and priority labels.</p>
    </td>
  </tr>
</table>

### Text Column

```python
{
    "key": "name",
    "title": "Name",
    "width": 160,
    "type": "text"
}
```

### Number Column

```python
{
    "key": "id",
    "title": "ID",
    "width": 60,
    "type": "number"
}
```

### Badge Column

```python
{
    "key": "permission",
    "title": "Permission",
    "width": 140,
    "type": "badge",
    "badge_colors": {
        "Admin": "red",
        "Manager": "blue",
        "Standard": "gray"
    }
}
```

---

## Row Data

Rows are passed as a list of dictionaries.

```python
rows = [
    {
        "id": 1,
        "first_name": "Harry",
        "last_name": "Gomm",
        "position": "Manager",
        "permission": "Manager"
    }
]
```

Each row key should match the `key` value defined in the column configuration.

---

## Use Cases

`CTkDataTable` can be used for:

* Admin panels
* User management screens
* Database viewers
* Desktop dashboards
* CRUD applications
* Job management tools
* NCR tracking systems
* Stock or asset registers
* Reporting interfaces
* Internal business systems

---

## Example Project Structure

```text
your-project/
├── app.py
├── assets/
│   ├── ctkdatatable-preview.png
│   └── ctkdatatable-badges-preview.png
├── database/
│   └── database.py
└── README.md
```

---

## Roadmap

Planned improvements may include:

* Column sorting
* Searching and filtering
* Row selection
* Action buttons
* Pagination
* Editable cells
* Custom themes
* Improved scrollbars
* More column types
* More documentation examples

---

## Project Status

`CTkDataTable` is currently in development.

It is being improved through practical use in real CustomTkinter desktop application projects. Feedback, issues and suggestions are welcome.

---

## Contributing

Contributions are welcome.

If you find a bug, have an idea for a feature, or want to improve the documentation, feel free to open an issue or submit a pull request.

---

## Licence

This project is released under the MIT Licence.

---

## Links

<p>
  <a href="https://pypi.org/project/CTkDataTable/">
    <img src="https://img.shields.io/badge/PyPI-CTkDataTable-7c3aed?style=for-the-badge&amp;logo=pypi&amp;logoColor=white" />
  </a>
  <a href="https://github.com/Harry-g25/CTkDataTable">
    <img src="https://img.shields.io/badge/GitHub-Repository-111827?style=for-the-badge&amp;logo=github&amp;logoColor=white" />
  </a>
  <a href="https://www.harrygomm.co.uk">
    <img src="https://img.shields.io/badge/Portfolio-harrygomm.co.uk-312e81?style=for-the-badge&amp;logo=google-chrome&amp;logoColor=white" />
  </a>
</p>

---

<div align="center">

### Built for clean, practical CustomTkinter applications.

<img src="https://capsule-render.vercel.app/api?type=rect&amp;height=90&amp;section=footer&amp;color=0:312e81,50:111827,100:020617" />

</div>
