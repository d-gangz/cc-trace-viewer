# MonsterUI Component Library Reference

Taken from this [Elite AI assisted coding blog post](https://elite-ai-assisted-coding.dev/p/agentic-coding-fasthtml-app-evals)

## Overview

MonsterUI is FastHTML's component library built on top of UIKit and FrankenUI, providing pre-built, customizable UI components following modern design principles.

**Key Principles:**

- Built on UIKit and FrankenUI foundation
- Works seamlessly with Tailwind CSS
- Use Tailwind for spacing (margin, padding, gap)
- Use MonsterUI components for everything else when possible

## Core Import Pattern

```python
from fasthtml.common import *
from monsterui.all import *
from fasthtml.svg import *  # If using icons

# Standard app initialization with theme
app, rt = fast_app(hdrs=Theme.blue.headers())
```

## Component API Reference

### Style Enums

#### Text Styling

- **`TextT`**: Text styles (paragraph, lead, meta, gray, italic, xs, sm, lg, xl, light, normal, medium, bold, extrabold, muted, primary, secondary, success, warning, error, info, left, right, center, justify, start, end, top, middle, bottom, truncate, break\_, nowrap, underline, highlight)

#### Button Styling

- **`ButtonT`**: Button styles (default, ghost, primary, secondary, destructive, text, link, xs, sm, lg, xl, icon)

#### Container Sizing

- **`ContainerT`**: Container max widths (xs, sm, lg, xl, expand)

#### Section Styling

- **`SectionT`**: Section styles (default, muted, primary, secondary, xs, sm, lg, xl, remove_vertical)

#### Link Styling

- **`AT`**: Link/anchor styles (muted, text, reset, primary, classic)

#### List Styling

- **`ListT`**: List styles (disc, circle, square, decimal, hyphen, bullet, divider, striped)

#### Label Styling

- **`LabelT`**: Label/pill styles (primary, secondary, destructive)

#### Navigation Styling

- **`NavT`**: Navigation styles (default, primary, secondary)
- **`ScrollspyT`**: Scrollspy styles (underline, bold)

#### Card Styling

- **`CardT`**: Card styles (default, primary, secondary, destructive, hover)

#### Table Styling

- **`TableT`**: Table styles (divider, striped, hover, sm, lg, justify, middle, responsive)

### Core Components

#### Layout Components

- **`Container`**: Main content wrapper for large sections
- **`Section`**: Section with styling and margins
- **`Grid`**: Responsive grid layout with smart defaults
- **`Button`**: Styled button (defaults to submit for forms)

#### Flexbox Layout Helpers

- **`DivFullySpaced`**: Flex container with maximum space between items
- **`DivCentered`**: Flex container with centered items
- **`DivLAligned`**: Flex container with left-aligned items
- **`DivRAligned`**: Flex container with right-aligned items
- **`DivVStacked`**: Flex container with vertically stacked items

### Form Components

#### Basic Form Elements

- **`Form`**: Form with default spacing between elements
- **`Fieldset`**: Styled fieldset container
- **`Legend`**: Styled legend for fieldsets
- **`Input`**: Styled text input
- **`TextArea`**: Styled textarea
- **`Radio`**: Styled radio button
- **`CheckboxX`**: Styled checkbox
- **`Range`**: Styled range slider
- **`Switch`**: Toggle switch component
- **`Select`**: Dropdown select with optional search
- **`Upload`**: File upload component
- **`UploadZone`**: Drag-and-drop file zone

#### Form Labels & Combos

- **`FormLabel`**: Styled form label
- **`Label`**: Pill-style labels (FrankenUI)
- **`LabelInput`**: Label + Input combo with proper spacing/linking
- **`LabelSelect`**: Label + Select combo with proper spacing/linking
- **`LabelRadio`**: Label + Radio combo with proper spacing/linking
- **`LabelCheckboxX`**: Label + Checkbox combo with proper spacing/linking
- **`LabelTextArea`**: Label + TextArea combo with proper spacing/linking

#### Form Helpers

- **`Options`**: Wrap items into Option elements for Select
- **`UkFormSection`**: Form section with title and description

### Navigation Components

- **`NavBar`**: Responsive navigation bar with mobile menu support
- **`NavContainer`**: Navigation list container (for sidebars)
- **`NavParentLi`**: Navigation item with nested children
- **`NavDividerLi`**: Navigation divider item
- **`NavHeaderLi`**: Navigation header item
- **`NavSubtitle`**: Navigation subtitle element
- **`NavCloseLi`**: Navigation item with close button
- **`DropDownNavContainer`**: Dropdown menu container

### Modal & Dialog Components

- **`Modal`**: Modal dialog with proper structure
- **`ModalTitle`**: Modal title element
- **`ModalCloseButton`**: Button that closes modal via JS

### Data Display Components

- **`Card`**: Card with header, body, and footer sections
- **`Table`**: Basic table component
- **`TableFromLists`**: Create table from list of lists
- **`TableFromDicts`**: Create table from list of dictionaries (recommended)

### Icons & Avatars

- **`UkIcon`**: Lucide icon component
- **`UkIconLink`**: Clickable icon link
- **`DiceBearAvatar`**: Generated avatar from DiceBear API

### Utility Functions

- **`render_md`**: Render markdown content with proper styling
- **`apply_classes`**: Apply classes to HTML string

## Common Component Patterns

### Card with Content

```python
def Tags(cats): return DivLAligned(map(Label, cats))

Card(
    DivLAligned(
        A(Img(src="https://picsum.photos/200/200?random=12", style="width:200px"),href="#"),
        Div(cls='space-y-3 uk-width-expand')(
            H4("Creating Custom FastHTML Tags for Markdown Rendering"),
            P("A step by step tutorial to rendering markdown in FastHTML using zero-md inside of DaisyUI chat bubbles"),
            DivFullySpaced(map(Small, ["Isaac Flath", "20-October-2024"]), cls=TextT.muted),
            DivFullySpaced(
                Tags(["FastHTML", "HTMX", "Web Apps"]),
                Button("Read", cls=(ButtonT.primary,'h-6'))))),
    cls=CardT.hover)
```

### Form with Grid Layout

```python
relationship = ["Parent",'Sibling', "Friend", "Spouse", "Significant Other", "Relative", "Child", "Other"]
Div(cls='space-y-4')(
    DivCentered(
        H3("Emergency Contact Form"),
        P("Please fill out the form completely", cls=TextPresets.muted_sm)),
    Form(cls='space-y-4')(
        Grid(LabelInput("First Name",id='fn'), LabelInput("Last Name",id='ln')),
        Grid(LabelInput("Email",     id='em'), LabelInput("Phone",    id='ph')),
        H3("Relationship to patient"),
        Grid(*[LabelCheckboxX(o) for o in relationship], cols=4, cls='space-y-3'),
        LabelInput("Address",        id='ad'),
        LabelInput("Address Line 2", id='ad2'),
        Grid(LabelInput("City",      id='ct'), LabelInput("State",    id='st')),
        LabelInput("Zip",            id='zp'),
        DivCentered(Button("Submit Form", cls=ButtonT.primary))))
```

### Navigation Bar

```python
NavBar(
    A(Input(placeholder='search')),
    A(UkIcon("rocket")),
    A('Page1',href='/rt1'),
    A("Page2", href='/rt3'),
    brand=DivLAligned(Img(src='/api_reference/logo.svg'),UkIcon('rocket',height=30,width=30)))
```

## Quick Reference Guide

### Application Setup

```python
from fasthtml.common import *
from monsterui.all import *

# Basic app setup with theme
app, rt = fast_app(hdrs=Theme.blue.headers())

# With additional features
app, rt = fast_app(hdrs=Theme.blue.headers(), pico=False, live=True, HighlightJS=True)
```

### Database Pattern (FastLite)

```python
from pathlib import Path

# Define data models as simple classes
class Query:
    id: int          # Primary key
    query_text: str
    created_at: str

# Create database and tables
db = database(Path("myapp.db"))
db.queries = db.create(Query, pk='id')

# CRUD operations
db.queries.insert(Query(query_text="test", created_at=datetime.now().isoformat()))
db.queries('query_text=?', ["test"])  # Query with conditions
db.q("SELECT * FROM query WHERE id=?", [1])  # Raw SQL when needed
```

### Routing Pattern

```python
@rt
def index():
    return layout(content)

@rt
def view_item(item_id: int):
    return layout(item_details)

# Route with parameters
@rt
def save_data(query_id: str, result_id: str, rating: int = 0):
    # FastHTML auto-converts form data to function parameters
    return response
```

### HTMX Integration

```python
# Form submission
Form(
    Input(id="query"),
    Button("Submit"),
    hx_post=search,              # POST to search route
    hx_target="#results",        # Update #results div
    hx_swap="innerHTML"          # Replace content
)

# Dynamic updates
Button("Save",
    hx_post=save_eval.to(query_id=1, result_id=2),  # Pass parameters
    hx_swap="none")  # No DOM update
```

### UI Components

#### Layout Components

```python
# Navigation
NavBar(
    A("Home", href="/"),
    A("About", href="/about"),
    brand=H3("My App"),
    sticky=True
)

# Container layouts
Container(content)                    # Standard container
DivFullySpaced(left, right)          # Flexbox space-between
DivLAligned(icon, text)              # Left-aligned flex
DivRAligned(buttons)                 # Right-aligned flex
DivCentered(content)                 # Centered content
```

#### Forms

```python
# Styled form inputs
LabelInput("Name", id="name", placeholder="Enter name")
LabelSelect(Option("A"), Option("B"), label="Choose", id="choice")
LabelTextArea("Notes", id="notes", rows="3")
LabelCheckboxX("Agree", id="agree")
LabelRadio("Option 1", name="group", value="1")

# Form structure
Form(
    Grid(
        Div(LabelInput(...)),
        Div(LabelSelect(...)),
        cols=2
    ),
    Button("Submit", cls=ButtonT.primary)
)
```

#### Data Display

```python
# Cards
Card(
    content,
    header=(H3("Title"), Subtitle("Description")),
    footer=Button("Action")
)

# Tables from dictionaries
headers = ["Name", "Email", "Actions"]
rows = [
    {"Name": "John", "Email": "john@example.com", "Actions": A("Edit")}
]
TableFromDicts(headers, rows)

# Custom table rendering
def cell_render(col, val):
    match col:
        case "Actions": return Td(Button("Edit"))
        case _: return Td(val)

TableFromDicts(headers, data, body_cell_render=cell_render)
```

#### Modals & Dropdowns

```python
# Modal
Modal(
    Div(
        ModalTitle("Create Item"),
        Form(...),
        DivRAligned(
            ModalCloseButton("Cancel"),
            ModalCloseButton("Save", cls=ButtonT.primary)
        )
    ),
    id="create-modal"
)

# Dropdown
DropDownNavContainer(
    NavCloseLi(A("Option 1")),
    NavCloseLi(A("Option 2"))
)
```

### Common Patterns

#### Page Layout Pattern

```python
def layout(content):
    return Div(
        NavBar(...),
        Container(content),
        cls="min-h-screen"
    )

@rt
def index():
    return layout(
        H1("Welcome"),
        Grid(cards, cols_lg=3)
    )
```

#### Search/Filter Pattern

```python
def search_form():
    return Form(
        LabelInput("Query", id="query"),
        LabelSelect(...options..., id="filter"),
        Button("Search"),
        hx_post=search,
        hx_target="#results"
    )

@rt
def search(query: str, filter: str):
    results = perform_search(query, filter)
    return Div(
        *[ResultCard(r) for r in results],
        id="results"
    )
```

#### CRUD Operations Pattern

```python
# Create
@rt
def create_item(name: str, description: str):
    item = db.items.insert(Item(name=name, description=description))
    return Success("Item created")

# Read
@rt
def view_items():
    items = db.items()  # Get all
    return Grid(*[ItemCard(i) for i in items])

# Update
@rt
def update_item(item_id: int, **kwargs):
    db.items.update(item_id, **kwargs)
    return Success("Updated")

# Delete
@rt
def delete_item(item_id: int):
    db.items.delete(item_id)
    return Success("Deleted")
```

#### File Upload Pattern

```python
# Reading files in artifacts
content = await window.fs.readFile('filename.csv', {'encoding': 'utf8'})

# Processing CSV files
import Papa from 'papaparse'
parsed = Papa.parse(content, {
    header: True,
    dynamicTyping: True,
    skipEmptyLines: True
})
```

### Styling

#### Theme Classes

- **ButtonT**: `primary`, `ghost` - Button styles
- **TextT**: `muted`, `error`, `sm` - Text styles
- **CardT**: `hover` - Card hover effects
- **NavT**: `primary`, `secondary` - Navigation styles
- **ContainerT**: `xl` - Container sizes

#### Common CSS Classes

- `space-y-4` - Vertical spacing
- `w-full` - Full width
- `gap-4` - Grid gap
- `mt-4`, `mb-6` - Margins
- `rounded-md` - Border radius

### Best Practices

1. Use styled MonsterUI components over raw HTML when available
2. Leverage HTMX for dynamic updates without full page reloads
3. Use FastLite for simple database operations
4. Match route parameters to form field names for automatic binding
5. Compose layouts with reusable functions
6. Use Grid/Flex helpers (DivFullySpaced, DivCentered, etc.) for consistent layouts
7. Prefer dictionaries for table data with TableFromDicts
8. Keep forms simple with Label\* components that combine labels and inputs

### Quick Start Template

```python
from fasthtml.common import *
from monsterui.all import *
from datetime import datetime

app, rt = fast_app(hdrs=Theme.blue.headers())

# Database setup
db = database("app.db")
db.items = db.create(Item, pk='id')

# Layout wrapper
def layout(content):
    return Div(
        NavBar(A("Home", href="/"), brand=H3("My App")),
        Container(content)
    )

# Main route
@rt
def index():
    items = db.items()
    return layout(
        H1("Items"),
        Grid(*[ItemCard(i) for i in items])
    )

serve()
```

## Complete Table Example

```python
"""FrankenUI Tasks Example built with MonsterUI (original design by ShadCN)"""

from fasthtml.common import *
from monsterui.all import *
from fasthtml.svg import *
import json

app, rt = fast_app(hdrs=Theme.blue.headers())

def LAlignedCheckTxt(txt): return DivLAligned(UkIcon(icon='check'), P(txt, cls=TextPresets.muted_sm))

with open('data/status_list.json', 'r') as f: data     = json.load(f)
with open('data/statuses.json',    'r') as f: statuses = json.load(f)

def _create_tbl_data(d):
    return {'Done': d['selected'], 'Task': d['id'], 'Title': d['title'],
            'Status'  : d['status'], 'Priority': d['priority'] }

data = [_create_tbl_data(d)  for d in data]
page_size = 15
current_page = 0
paginated_data = data[current_page*page_size:(current_page+1)*page_size]

priority_dd = [{'priority': "low", 'count': 36 }, {'priority': "medium", 'count': 33 }, {'priority': "high", 'count': 31 }]

status_dd = [{'status': "backlog", 'count': 21 },{'status': "todo", 'count': 21 },{'status': "progress", 'count': 20 },{'status': "done",'count': 19 },{'status': "cancelled", 'count': 19 }]

def create_hotkey_li(hotkey): return NavCloseLi(A(DivFullySpaced(hotkey[0], Span(hotkey[1], cls=TextPresets.muted_sm))))

hotkeys_a = (('Profile','⇧⌘P'),('Billing','⌘B'),('Settings','⌘S'),('New Team',''))
hotkeys_b = (('Logout',''), )

avatar_opts = DropDownNavContainer(
    NavHeaderLi(P('sveltecult'),NavSubtitle('leader@sveltecult.com')),
    NavDividerLi(),
    *map(create_hotkey_li, hotkeys_a),
    NavDividerLi(),
    *map(create_hotkey_li, hotkeys_b),)

def CreateTaskModal():
    return Modal(
        Div(cls='p-6')(
            ModalTitle('Create Task'),
            P('Fill out the information below to create a new task', cls=TextPresets.muted_sm),
            Br(),
            Form(cls='space-y-6')(
                Grid(Div(Select(*map(Option,('Documentation', 'Bug', 'Feature')), label='Task Type', id='task_type')),
                     Div(Select(*map(Option,('In Progress', 'Backlog', 'Todo', 'Cancelled', 'Done')), label='Status', id='task_status')),
                     Div(Select(*map(Option, ('Low', 'Medium', 'High')), label='Priority', id='task_priority'))),
                TextArea(label='Title', placeholder='Please describe the task that needs to be completed'),
                DivRAligned(
                    ModalCloseButton('Cancel', cls=ButtonT.ghost),
                    ModalCloseButton('Submit', cls=ButtonT.primary),
                    cls='space-x-5'))),
        id='TaskForm')

page_heading = DivFullySpaced(cls='space-y-2')(
            Div(cls='space-y-2')(
                H2('Welcome back!'),P("Here's a list of your tasks for this month!", cls=TextPresets.muted_sm)),
            Div(DiceBearAvatar("sveltcult",8,8),avatar_opts))

table_controls =(Input(cls='w-[250px]',placeholder='Filter task'),
     Button("Status"),
     DropDownNavContainer(map(NavCloseLi,[A(DivFullySpaced(P(a['status']), P(a['count'])),cls='capitalize') for a in status_dd])),
     Button("Priority"),
     DropDownNavContainer(map(NavCloseLi,[A(DivFullySpaced(LAlignedCheckTxt(a['priority']), a['count']),cls='capitalize') for a in priority_dd])),
     Button("View"),
     DropDownNavContainer(map(NavCloseLi,[A(LAlignedCheckTxt(o)) for o in ['Title','Status','Priority']])),
     Button('Create Task',cls=(ButtonT.primary, TextPresets.bold_sm), data_uk_toggle="target: #TaskForm"))

def task_dropdown():
    return Div(Button(UkIcon('ellipsis')),
               DropDownNavContainer(
                   map(NavCloseLi,[
                       *map(A,('Edit', 'Make a copy', 'Favorite')),
                        A(DivFullySpaced(*[P(o, cls=TextPresets.muted_sm) for o in ('Delete', '⌘⌫')]))])))
def header_render(col):
    match col:
        case "Done":    return Th(CheckboxX(), shrink=True)
        case 'Actions': return Th("",          shrink=True)
        case _:         return Th(col,         expand=True)

def cell_render(col, val):
    def _Td(*args,cls='', **kwargs): return Td(*args, cls=f'p-2 {cls}',**kwargs)
    match col:
        case "Done": return _Td(shrink=True)(CheckboxX(selected=val))
        case "Task":  return _Td(val, cls='uk-visible@s')  # Hide on small screens
        case "Title": return _Td(val, cls='font-medium', expand=True)
        case "Status" | "Priority": return _Td(cls='uk-visible@m uk-text-nowrap capitalize')(Span(val))
        case "Actions": return _Td(task_dropdown(), shrink=True)
        case _: raise ValueError(f"Unknown column: {col}")

task_columns = ["Done", 'Task', 'Title', 'Status', 'Priority', 'Actions']

tasks_table = Div(cls='mt-4')(
    TableFromDicts(
        header_data=task_columns,
        body_data=paginated_data,
        body_cell_render=cell_render,
        header_cell_render=header_render,
        sortable=True,
        cls=(TableT.responsive, TableT.sm, TableT.divider)))


def footer():
    total_pages = (len(data) + page_size - 1) // page_size
    return DivFullySpaced(
        Div('1 of 100 row(s) selected.', cls=TextPresets.muted_sm),
        DivLAligned(
            DivCentered(f'Page {current_page + 1} of {total_pages}', cls=TextT.sm),
            DivLAligned(*[UkIconLink(icon=i,  button=True) for i in ('chevrons-left', 'chevron-left', 'chevron-right', 'chevrons-right')])))

tasks_ui = Div(DivFullySpaced(DivLAligned(table_controls), cls='mt-8'), tasks_table, footer())

@rt
def index(): return Container(page_heading, tasks_ui, CreateTaskModal())

serve()
```
