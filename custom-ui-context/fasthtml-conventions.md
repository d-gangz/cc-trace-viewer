# FastHTML Development Guide

Taken from this [Elite AI assisted coding blog post](https://elite-ai-assisted-coding.dev/p/agentic-coding-fasthtml-app-evals)

## Framework Philosophy

FastHTML is designed for simplicity and developer experience in Python web development:

- **Simplicity over Complexity**: Minimal abstractions between Python and HTML
- **Developer Experience**: Fast feedback loops and intuitive APIs
- **Progressive Enhancement**: Build apps that work everywhere, enhance where possible
- **Python-First**: Leverage Python's strengths instead of fighting against them

## Project Structure

**IMPORTANT**: Prefer single-file applications. Only add files when there's massive benefit.

```
fasthtml-app/
├── main.py           # Main application file (preferred: everything here)
├── components/       # Reusable UI components (only if necessary)
├── routes/          # Route handlers (only for very large apps)
├── static/          # Static assets
├── models/          # Data models (only if complex)
└── README.md        # Project documentation
```

## Core Patterns

### Application Setup

```python
from fasthtml.common import *
from monsterui.all import *

app, rt = fast_app(hdrs=Theme.blue.headers())
```

### Routing

#### Basic Route

```python
@rt
def index():
    return Container(H1("Title"), content)
```

#### Parameterized Routes

```python
@rt
def detail(item_id: str):
    # Access via: detail.to(item_id="123")
    pass

@rt
def action(parent_id: str, child_id: int, action_type: str):
    # Access via: action.to(parent_id="x", child_id=1, action_type="update")
    pass
```

### Database (FastLite)

#### Table Definition

```python
class Record:
    parent_id: str
    child_id: int
    content: str
    metadata: str
    status: str

db = Database('app.db')
db.records = db.create(Record, pk=('parent_id', 'child_id'), transform=True)
```

#### CRUD Operations

```python
# Create
new_record = db.records.insert(Record(...))
# Note: insert() returns the dataclass instance, convert to dict if needed:
# new_record_dict = new_record.__dict__

# Read
record = db.records[parent_id, child_id]  # Single record (may return dataclass)
records = list(db.records.rows_where('parent_id=?', [parent_id]))  # Query
unique_items = list(db.records.rows_where(select='distinct parent_id, content'))  # Distinct

# Update - IMPORTANT: Handle dataclass objects properly
record = db.records[id]
# Convert dataclass to dict for modification
record_dict = record.__dict__ if hasattr(record, '__dict__') else record
record_dict['field'] = new_value
db.records.update(record_dict)

# Delete
db.records.delete(record_id)
```

### HTMX Integration

#### Auto-Save Input

```python
Input(value=record['field'],
      name='field',
      hx_post=update.to(id=record_id),
      hx_trigger='change')
```

#### Button with Target Update

```python
Button("Action",
       hx_post=process.to(id=item_id, action="approve"),
       hx_target="#result-123",
       cls=ButtonT.primary)
```

#### Dynamic Content Updates

```python
@rt
def update_section(item_id: str, value: str):
    # Process and return HTML to replace target
    return render_updated_content(item_id)
```

## Component Patterns

### Tables from Data

```python
# Build table data
body = []
for item in items:
    body.append({
        'Column1': item['field'],
        'Column2': A("Link", href=detail.to(id=item['id'])),
        'Column3': interactive_component(item)
    })

# Create table
TableFromDicts(['Column1', 'Column2', 'Column3'], body)
```

### Layout Composition

```python
Container(
    H1("Page Title"),
    Card(render_md(content)),  # Card with markdown
    DivLAligned(button1, button2)  # Aligned buttons
)
```

### Interactive Toggle Buttons

```python
def toggle_buttons(parent_id: str, item_id: int = None):
    target_id = f"#toggle-{parent_id}-{item_id}" if item_id else f"#toggle-{parent_id}"
    current_state = db.records[parent_id, item_id].status

    def create_button(label: str):
        return Button(label,
            hx_post=update_state.to(parent_id=parent_id, item_id=item_id, state=label.lower()),
            hx_target=target_id,
            cls=ButtonT.primary if current_state == label.lower() else ButtonT.secondary,
            submit=False)

    return DivLAligned(
        create_button("Option1"),
        create_button("Option2"),
        id=target_id[1:])  # Remove # for element id
```

## Styling Reference

### Theme Application

```python
fast_app(hdrs=Theme.blue.headers())
```

### Common Style Classes

- **Buttons**: `ButtonT.primary`, `ButtonT.secondary`, `ButtonT.ghost`
- **Text**: `TextT.muted`, `TextT.sm`, `TextT.bold`
- **Links**: `AT.primary`, `AT.muted`, `AT.reset`
- **Cards**: `CardT.hover`, `CardT.primary`
- **Layout**: `Container`, `DivLAligned`, `DivCentered`, `DivFullySpaced`

## Common Techniques

### Dynamic URLs with Parameters

```python
A("Link Text",
  cls=AT.primary,
  href=route_func.to(param1=value1, param2=value2))
```

### Conditional Styling

```python
cls=ButtonT.primary if condition else ButtonT.secondary
```

### HTMX Target IDs

```python
target_id = f"#component-{parent_id}-{child_id}"  # For hx_target
id=target_id[1:]  # For element id (remove #)
```

### Markdown Rendering

```python
render_md(text.replace('\\n', '\n'))
```

## Request Handling

### POST Route Pattern

```python
@rt
def update_field(parent_id: str, child_id: int, field_name: str):
    # FastHTML auto-converts form data to function parameters
    record = Record(parent_id=parent_id, child_id=child_id, field_name=field_name)
    db.records.update(record)
    return render_updated_component()  # Return HTML for HTMX
```

### Component Factory Pattern

```python
def create_interactive_element(data):
    """Reusable component factory."""
    return Component(
        property1=data['field1'],
        property2=data['field2'],
        hx_post=action.to(id=data['id']),
        hx_target=f"#element-{data['id']}")
```

## Best Practices

### Core Principles

1. **URL Generation**: Always use `.to()` method for parameterized routes
2. **Database Keys**: Use compound primary keys for hierarchical data
3. **HTMX Triggers**: `'change'` for inputs, default click for buttons
4. **Target IDs**: Prefix with `#` in hx_target, remove for element id
5. **Component Reuse**: Create factory functions for repeated UI patterns
6. **State Management**: Database as single source of truth
7. **Response Patterns**: Return only updated HTML for HTMX requests
8. **Database Objects**: Always convert dataclass instances to dicts when modifying
9. **HTMX Targets**: Ensure target elements always exist in the DOM

### Component-First Development

```python
# ❌ BAD: Inline everything
@rt
def index():
    return Main(*[Card(H1("Title"), P("Content"), cls="py-6 border-b mb-4") for t,c in items])

# ✅ GOOD: Reusable components
def ContentCard(title, content):
    return Card(title, content, cls="py-6 border-b mb-4")

@rt
def index():
    return Main(*[ContentCard(*item) for item in items])
```

### HTMX Best Practices

- Use `hx_` attributes for dynamic behavior
- Keep responses minimal (return only what changes)
- Use semantic HTML elements
- Let server handle state

## Server Startup

```python
serve()  # Start the FastHTML server
```
