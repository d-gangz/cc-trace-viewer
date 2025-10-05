<!--
Document Type: Planning
Purpose: Implementation plan for Claude Code Trace Viewer using FastHTML + MonsterUI
Context: Building a local web application to visualize Claude Code session traces
Key Topics: Architecture design, data models, UI components, routing, JSONL parsing
Target Use: Reference guide for implementing the trace viewer application
-->

# Claude Code Trace Viewer - FastHTML + MonsterUI Implementation

## Overview

A local web application to visualize Claude Code session traces stored in `/Users/gang/.claude/projects/`. Built with FastHTML and MonsterUI for a fully Python-based, server-rendered solution.

## Architecture (Local-First)

**Single FastHTML application** with no React/JavaScript frontend. Everything server-rendered with HTMX for dynamic updates.

### Technology Stack

- **Backend**: FastHTML (Python) - single application
- **UI Framework**: MonsterUI (Tailwind-based components)
- **Styling**: Built-in Tailwind CSS (via MonsterUI)
- **Interactivity**: HTMX (built into FastHTML)
- **Data**: Direct JSONL file parsing (no database needed)

## Data Structure Understanding

### Projects Directory Structure

```
/Users/gang/.claude/projects/
├── -Users-gang-CLIProxyAPI/
│   ├── 89b6496f-9eb2-49c0-87a8-732914965845.jsonl
│   ├── 3397ac25-5364-4e62-894b-9413c5acf2e9.jsonl
│   └── ...
├── -Users-gang-courses-rag-course-practice/
│   └── [session files].jsonl
└── [other projects]/
```

- **9 project folders** (each representing a working directory)
- **188 total session files** (`.jsonl` format)

### JSONL Session File Format

Each session file contains one JSON object per line:

```json
{"type": "summary", "summary": "Session title", "leafUuid": "..."}
{"type": "file-history-snapshot", "messageId": "...", "snapshot": {...}}
{"type": "user", "message": {"role": "user", "content": "..."}, "timestamp": "...", "uuid": "...", "parentUuid": "..."}
{"type": "assistant", "message": {"role": "assistant", "content": [...]}, "timestamp": "...", "uuid": "...", "parentUuid": "..."}
{"type": "system", "content": "...", "timestamp": "...", "uuid": "...", "parentUuid": "..."}
```

**Event Types:**

- `summary` - Session metadata (first line)
- `user` - User messages
- `assistant` - Assistant responses (may contain tool calls)
- `system` - System messages
- `file-history-snapshot` - File state snapshots

**Key Fields:**

- `uuid` - Unique identifier for each event
- `parentUuid` - Parent event UUID (for building tree structure)
- `timestamp` - ISO format timestamp
- `message` - Contains `role` and `content` (for user/assistant)
- `sessionId` - Session identifier
- `cwd` - Working directory
- `gitBranch` - Git branch name

## Application Structure

### Project Location

The trace viewer lives in **its own project folder** (separate from session data):

```
/Users/gang/cc-trace-viewer/    ← New project for the viewer
├── app.py              # Main FastHTML application
├── models.py           # Data models for sessions/traces
├── components.py       # Reusable UI components
├── static/
│   └── custom.css      # Custom styling for trace tree
└── requirements.txt    # Dependencies
```

### Data Access Pattern

The viewer **reads from multiple locations** on your local machine:

**Session Data:**

```
/Users/gang/.claude/projects/       ← Session JSONL files
├── -Users-gang-CLIProxyAPI/
│   ├── abc-123.jsonl
│   └── def-456.jsonl
└── -Users-gang-courses-rag-course-practice/
    └── xyz-789.jsonl
```

**CLAUDE.md Files (accessed based on session `cwd` field):**

```
/Users/gang/.claude/CLAUDE.md                   ← Global CLAUDE.md
/Users/gang/CLIProxyAPI/CLAUDE.md               ← Project-specific
/Users/gang/courses/rag-course-practice/CLAUDE.md
```

**How It Works:**

1. Viewer reads session JSONL from `/Users/gang/.claude/projects/`
2. Extracts `cwd` from session (e.g., `/Users/gang/CLIProxyAPI`)
3. Reads `CLAUDE.md` from that `cwd` directory
4. All file access is **local** (no network, no API, just Python file I/O)

**Configuration in app.py:**

```python
from pathlib import Path

# Hardcoded paths - change if needed
PROJECTS_DIR = Path("/Users/gang/.claude/projects")
GLOBAL_CLAUDE_MD = Path.home() / ".claude" / "CLAUDE.md"
```

## Features

### 1. Home Page - Combined Project List & Sessions (Accordion View)

**Route**: `/`

**Displays:**

- **Accordion-style layout** with all projects and their sessions on a single page
- Each project is an expandable/collapsible section showing:
  - **Project Header** (always visible):
    - Project name (e.g., "CLIProxyAPI")
    - Number of sessions
    - Last session date
    - Expand/collapse indicator
  - **Session List** (revealed when expanded):
    - Sessions sorted by recency (newest first)
    - Each session row shows:
      - Date & Time (YYYY-MM-DD HH:MM:SS)
      - Summary (from first line of JSONL)
      - Message count
      - Click to open trace viewer
- **Default state**: All projects collapsed, or most recent project expanded
- **No navigation required**: Everything accessible from one page

**Layout:**

```
Claude Code Trace Viewer
├─ ▼ CLIProxyAPI (4 sessions, last: 2025-09-30 11:11)
│   ├─ 2025-09-30 11:11 - "Session about..."  [15 msgs] → [Click to view trace]
│   ├─ 2025-09-30 10:58 - "Model setup..."    [10 msgs] → [Click to view trace]
│   ├─ 2025-09-30 10:54 - "Bug fix..."        [75 msgs] → [Click to view trace]
│   └─ 2025-09-30 10:38 - "Initial setup..."  [3 msgs]  → [Click to view trace]
├─ ► RAG Course Practice (21 sessions, last: 2025-10-04 18:22)
├─ ► Personal Bizos (100 sessions, last: 2025-10-05 11:01)
└─ ► Other Projects...
```

**Implementation:**

```python
@rt("/")
def index():
    """
    Combined home page with accordion view of projects and sessions
    """
    projects = scan_projects()  # Returns list[Project] with sessions loaded

    return Titled("Claude Code Trace Viewer",
        Container(
            # Accordion container
            *[ProjectAccordion(project) for project in projects],
            cls="space-y-4"))

def ProjectAccordion(project: Project):
    """
    Accordion section for a single project with its sessions
    """
    # Generate unique ID for accordion
    accordion_id = f"project-{project.folder_name}"

    return Div(
        # Project header (clickable to expand/collapse)
        Div(
            DivHStacked(
                UkIcon("chevron-down", cls="accordion-icon"),
                H3(project.name, cls="text-xl font-bold"),
                Span(f"{project.session_count} sessions",
                     cls="text-sm text-gray-400"),
                Span(f"Last: {project.last_session.strftime('%Y-%m-%d %H:%M')}",
                     cls="text-sm text-gray-500")),
            cls="project-header cursor-pointer p-4 bg-gray-800 rounded hover:bg-gray-700",
            hx_get=f"/toggle-project/{project.folder_name}",
            hx_target=f"#{accordion_id}-content",
            hx_swap="outerHTML"),

        # Session list (initially hidden or loaded via HTMX)
        Div(
            SessionList(project.sessions) if project.expanded else None,
            id=f"{accordion_id}-content",
            cls="accordion-content"),

        cls="project-accordion")

def SessionList(sessions: list[Session]):
    """
    List of sessions for a project (sorted by recency)
    """
    return Div(
        *[SessionRow(session) for session in sessions],
        cls="session-list p-4 bg-gray-900 rounded-b")

def SessionRow(session: Session):
    """
    Single session row - clickable to open trace viewer
    """
    return Div(
        DivHStacked(
            Span(session.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                 cls="text-sm font-mono text-gray-400 w-40"),
            Span(session.summary[:60] + "..." if len(session.summary) > 60 else session.summary,
                 cls="flex-1 text-gray-200"),
            Span(f"{session.message_count} msgs",
                 cls="text-xs text-gray-500 w-20 text-right")),
        cls="session-row p-3 hover:bg-gray-800 rounded cursor-pointer border-b border-gray-700",
        hx_get=f"/session/{session.id}",
        hx_target="body",
        hx_swap="innerHTML",
        hx_push_url="true")  # Update URL for browser back button

@rt("/toggle-project/{project_name}")
def toggle_project(project_name: str):
    """
    HTMX endpoint to toggle project accordion (load/hide sessions)
    """
    project = get_project(project_name)

    if project.expanded:
        # Collapse: return empty div
        return Div(id=f"project-{project_name}-content", cls="accordion-content")
    else:
        # Expand: return session list
        sessions = load_sessions(project_name)
        return SessionList(sessions)
```

### 2. Trace Viewer - Full Session Detail

**Route**: `/session/{session_id}`

**Layout:** Two-panel design matching the screenshot

#### Left Panel - Trace Tree

Collapsible tree structure showing:

- User messages (chat icon)
- Assistant responses (bot icon)
- Tool calls (tool icon, expandable)
  - Tool use details (nested)
  - Tool results (nested)
- System messages (info icon)

Each node displays:

- Type icon
- Event type label
- Timing information
- Token counts (for LLM messages with `usage` field)
- Expand/collapse for nested content

**Tree Structure:**

```
📝 user - 10:39:34
  ├─ 🤖 assistant - 10:39:38
  │   ├─ 🔧 Read (tool call)
  │   │   └─ ✓ tool result
  │   └─ 🔧 Grep (tool call)
  │       └─ ✓ tool result
  ├─ 📝 user - 10:40:12
  └─ 🤖 assistant - 10:40:15
```

#### Right Panel - Detail View

Shows full content when clicking any trace event:

- **Tabs for Input/Output** (similar to screenshot)
- **Syntax highlighting** for:
  - Markdown (user/assistant messages)
  - JSON (tool inputs/outputs)
  - Code blocks (within messages)
- **Session Context Panel** (top of right panel):
  - Claude Code version (e.g., "v2.0.0")
  - Session timestamp
  - Working directory
  - Git branch
  - Current CLAUDE.md files (with warning they may have changed)
  - Git command helper for finding commit at session time
- **Copy buttons** for content

**HTMX Integration:**

```python
@rt("/session/{session_id}")
def session_trace(session_id: str):
    trace_events = parse_session_file(session_id)
    return Container(
        DivHStacked(
            TraceTree(trace_events),
            DetailPanel(trace_events[0] if trace_events else None)))

@rt("/trace-node/{uuid}")
def trace_node_detail(uuid: str, session_id: str):
    # HTMX endpoint to load detail panel for clicked node
    event = get_event_by_uuid(session_id, uuid)
    return DetailPanel(event)
```

### 3. Session Context Panel - CLAUDE.md & Git Navigation

**Purpose**: Help users understand the context that was active during a session and provide clues to find the exact project state.

**What's Available in Session Files:**

- ✅ Claude Code version (e.g., "2.0.0") - exact version running during session
- ✅ Working directory (e.g., "/Users/gang/CLIProxyAPI")
- ✅ Git branch (e.g., "main")
- ✅ Timestamp (e.g., "2025-09-30 10:39:34")
- ❌ NOT available: Commit hash, CLAUDE.md snapshot, system prompt

**What the Viewer Shows:**

**Session Context Panel (displayed at top of trace viewer):**

```
┌──────────────────────────────────────────────────────────────┐
│ Session Context                                               │
├──────────────────────────────────────────────────────────────┤
│ ⚙️  Claude Code Version: v2.0.0                              │
│ 📅 Session Time: 2025-09-30 10:39:34                         │
│ 📂 Working Directory: /Users/gang/CLIProxyAPI                │
│ 🌿 Git Branch: main                                          │
│                                                               │
│ 📄 CLAUDE.md Files (current state - may have changed):       │
│    [View Global CLAUDE.md] [View Project CLAUDE.md]          │
│                                                               │
│ 💡 Find exact project state at session time:                 │
│    cd /Users/gang/CLIProxyAPI                                │
│    git log --before="2025-09-30 10:40:00" \                  │
│            --after="2025-09-30 10:35:00" -n 5                │
│    [Copy Command]                                             │
└──────────────────────────────────────────────────────────────┘
```

**Implementation:**

```python
def get_session_context(session_id: str) -> dict:
    """
    Retrieve session context including CLAUDE.md files and git navigation hints

    Input data sources: Session JSONL file, local CLAUDE.md files
    Output destinations: Session context dictionary
    Dependencies: pathlib, datetime
    Key exports: get_session_context()
    Side effects: Reads CLAUDE.md files from disk
    """
    # Parse session to get metadata
    events = parse_session_file(session_id)
    first_event = events[0] if events else {}

    context = {
        'version': first_event.get('version'),
        'timestamp': first_event.get('timestamp'),
        'cwd': first_event.get('cwd'),
        'git_branch': first_event.get('git_branch'),
        'session_id': first_event.get('sessionId'),
        'project_claude_md': None,
        'global_claude_md': None,
        'git_command': None
    }

    # Try to read project CLAUDE.md (current state)
    if context['cwd']:
        project_claude_path = Path(context['cwd']) / 'CLAUDE.md'
        if project_claude_path.exists():
            context['project_claude_md'] = project_claude_path.read_text()

    # Read global CLAUDE.md (current state)
    global_claude_path = Path.home() / '.claude' / 'CLAUDE.md'
    if global_claude_path.exists():
        context['global_claude_md'] = global_claude_path.read_text()

    # Generate git command for finding commit at session time
    if context['timestamp'] and context['cwd']:
        timestamp = datetime.fromisoformat(context['timestamp'])
        before = (timestamp + timedelta(minutes=5)).strftime('%Y-%m-%d %H:%M:%S')
        after = (timestamp - timedelta(minutes=5)).strftime('%Y-%m-%d %H:%M:%S')

        context['git_command'] = (
            f'cd {context["cwd"]}\n'
            f'git log --before="{before}" --after="{after}" -n 5'
        )

    return context

def SessionContextPanel(context: dict):
    """
    Displays session context with CLAUDE.md and git navigation
    """
    return Card(
        H3("Session Context", cls="text-lg font-bold mb-4"),

        # Metadata
        Div(
            P(f"⚙️  Claude Code Version: v{context['version']}"),
            P(f"📅 Session Time: {context['timestamp']}"),
            P(f"📂 Working Directory: {context['cwd']}"),
            P(f"🌿 Git Branch: {context['git_branch']}"),
            cls="space-y-2 mb-4"),

        # CLAUDE.md files
        Div(
            P("📄 CLAUDE.md Files (current state - may have changed):",
              cls="font-semibold text-yellow-400 mb-2"),
            DivHStacked(
                Button("View Global CLAUDE.md",
                       hx_get=f"/view-claude-md?type=global",
                       hx_target="#claude-md-modal",
                       cls="btn-sm"),
                Button("View Project CLAUDE.md",
                       hx_get=f"/view-claude-md?type=project&cwd={context['cwd']}",
                       hx_target="#claude-md-modal",
                       cls="btn-sm") if context['project_claude_md'] else None,
                cls="gap-2"),
            cls="mb-4"),

        # Git navigation helper
        Div(
            P("💡 Find exact project state at session time:",
              cls="font-semibold mb-2"),
            Pre(
                Code(context['git_command'], cls="text-sm"),
                cls="bg-gray-900 p-3 rounded"),
            Button("Copy Command",
                   onclick=f"navigator.clipboard.writeText({repr(context['git_command'])})",
                   cls="btn-sm mt-2"),
            cls="mb-4"),

        cls="bg-gray-800 p-4 rounded mb-4")

@rt("/view-claude-md")
def view_claude_md(type: str, cwd: str = None):
    """
    HTMX endpoint to show CLAUDE.md content in a modal
    """
    if type == "global":
        path = Path.home() / '.claude' / 'CLAUDE.md'
        title = "Global CLAUDE.md"
    else:
        path = Path(cwd) / 'CLAUDE.md'
        title = f"Project CLAUDE.md ({Path(cwd).name})"

    if not path.exists():
        content = "File not found"
    else:
        content = path.read_text()

    return Modal(
        H3(title, cls="text-xl font-bold mb-4"),
        P("⚠️ Warning: This is the CURRENT state. It may have changed since the session.",
          cls="text-yellow-400 mb-4"),
        Pre(Code(content, cls="language-markdown"),
            cls="bg-gray-900 p-4 rounded overflow-auto max-h-96"),
        Button("Close", cls="btn-primary mt-4"),
        id="claude-md-modal")
```

**Key Features:**

1. **Claude Code Version Display**: Shows exact version (e.g., "v2.0.0") that was running
2. **Current CLAUDE.md Files**: Shows current state with clear warning
3. **Git Navigation Helper**: Provides ready-to-copy git command to find commits around session time
4. **Timestamp-Based Search**: Uses session timestamp ±5 minutes to narrow down commits
5. **Modal View**: Click to view full CLAUDE.md content without leaving trace viewer

**User Workflow:**

1. Open session trace viewer
2. See session context panel at top
3. View current CLAUDE.md as reference
4. Copy git command to find exact commit
5. Run command in terminal to find commit hash
6. Checkout commit or browse on GitHub to see exact CLAUDE.md state

### 4. Timing & Token Usage Features

**Purpose**: Provide detailed performance metrics and token consumption analysis for each session.

**What's Available from Session Files:**

✅ **Timestamps** - Every event has ISO-formatted timestamp

```json
"timestamp": "2025-09-30T02:39:34.496Z"
```

✅ **Token Usage** - Assistant messages include detailed usage metadata

```json
"usage": {
  "input_tokens": 4,
  "cache_creation_input_tokens": 24171,
  "cache_read_input_tokens": 0,
  "output_tokens": 5,
  "service_tier": "standard"
}
```

❌ **NOT Available** - No explicit duration field (we calculate it)

**Calculated Metrics:**

1. **Response Time**: Duration between user message and assistant response
2. **Tool Execution Time**: Duration between tool call and tool result
3. **Total Session Duration**: First event timestamp to last event timestamp
4. **Total Token Consumption**: Sum of all tokens across entire session

**Display in Trace Tree:**

```
📝 user - 10:39:34 (3.6s)          ← Duration to next event
  └─ 🤖 assistant - 10:39:38       ← 24,180 tok (hover for breakdown)
      ├─ 🔧 Read - 10:39:38 (0.3s)
      │   └─ ✓ result - 10:39:39
      └─ 🔧 Grep - 10:39:39 (0.2s)
          └─ ✓ result - 10:39:39

📝 user - 10:40:12 (4.2s)
  └─ 🤖 assistant - 10:40:16       ← 1,661 tok
```

**Display in Detail Panel:**

When clicking an assistant message with token usage:

```
🪙 Token Usage:
  • Input Tokens: 4
  • Cache Creation: 24,171
  • Cache Read: 0
  • Output Tokens: 5
  • Total: 24,180
```

**Token Breakdown Explanation:**

- **Input Tokens**: Regular input tokens processed
- **Cache Creation**: Tokens used to create prompt cache (first use)
- **Cache Read**: Tokens read from prompt cache (subsequent uses)
- **Output Tokens**: Tokens generated in response

**Implementation:**

```python
# In TraceEvent model
@property
def token_breakdown(self) -> dict:
    """Detailed token usage breakdown"""
    if not self.usage:
        return {}

    return {
        'input_tokens': self.usage.get('input_tokens', 0),
        'cache_creation_input_tokens': self.usage.get('cache_creation_input_tokens', 0),
        'cache_read_input_tokens': self.usage.get('cache_read_input_tokens', 0),
        'output_tokens': self.usage.get('output_tokens', 0),
        'total_tokens': (
            self.usage.get('input_tokens', 0) +
            self.usage.get('cache_creation_input_tokens', 0) +
            self.usage.get('cache_read_input_tokens', 0) +
            self.usage.get('output_tokens', 0)
        )
    }

def duration_to(self, next_event: 'TraceEvent') -> float:
    """Calculate duration in seconds to next event"""
    if not next_event or not next_event.timestamp:
        return 0
    delta = next_event.timestamp - self.timestamp
    return delta.total_seconds()
```

**Session Summary Statistics:**

At the top of the trace viewer, show:

- **Total Duration**: 5m 42s
- **Total Turns**: 12 (user + assistant exchanges)
- **Total Tokens**: 156,234
- **Average Response Time**: 3.8s

## Data Models

### Project Model

```python
@dataclass
class Project:
    name: str              # Human-readable name (e.g., "CLIProxyAPI")
    path: str              # Full path to project folder
    folder_name: str       # Original folder name
    session_count: int     # Number of .jsonl files
    last_session: datetime # Most recent session timestamp
```

### Session Model

```python
@dataclass
class Session:
    id: str                # Session UUID (filename without .jsonl)
    project: str           # Project folder name
    summary: str           # Session summary from first line
    timestamp: datetime    # First event timestamp
    message_count: int     # Total number of events
    first_user_message: str # Preview of first user message
    file_path: str         # Full path to .jsonl file
```

### TraceEvent Model

```python
@dataclass
class TraceEvent:
    uuid: str                      # Event UUID
    parent_uuid: str | None        # Parent event UUID (for tree)
    type: str                      # user, assistant, system, etc.
    timestamp: datetime            # Event timestamp
    content: Any                   # Message content or system content

    # Optional fields
    message: dict | None           # Full message object (user/assistant)
    tool_calls: list[dict] | None  # Tool calls (for assistant messages)
    tool_use_id: str | None        # Tool use ID (for tool results)
    usage: dict | None             # Token usage (for LLM calls)
    session_id: str                # Session identifier
    cwd: str | None                # Working directory
    git_branch: str | None         # Git branch

    # Tree structure
    children: list['TraceEvent']   # Child events

    @property
    def token_count(self) -> int:
        """Total tokens (input + output)"""
        if self.usage:
            return self.usage.get('input_tokens', 0) + \
                   self.usage.get('output_tokens', 0)
        return 0

    @property
    def has_output(self) -> bool:
        """Check if event has output content"""
        return bool(self.message and
                   self.message.get('role') == 'assistant')

    @property
    def token_breakdown(self) -> dict:
        """
        Detailed token usage breakdown

        Returns dict with:
        - input_tokens: Regular input tokens
        - cache_creation_input_tokens: Tokens used to create cache
        - cache_read_input_tokens: Tokens read from cache
        - output_tokens: Generated output tokens
        - total_tokens: Sum of all tokens
        """
        if not self.usage:
            return {}

        return {
            'input_tokens': self.usage.get('input_tokens', 0),
            'cache_creation_input_tokens': self.usage.get('cache_creation_input_tokens', 0),
            'cache_read_input_tokens': self.usage.get('cache_read_input_tokens', 0),
            'output_tokens': self.usage.get('output_tokens', 0),
            'total_tokens': (
                self.usage.get('input_tokens', 0) +
                self.usage.get('cache_creation_input_tokens', 0) +
                self.usage.get('cache_read_input_tokens', 0) +
                self.usage.get('output_tokens', 0)
            )
        }

    def duration_to(self, next_event: 'TraceEvent') -> float:
        """Calculate duration in seconds to next event"""
        if not next_event or not next_event.timestamp:
            return 0
        delta = next_event.timestamp - self.timestamp
        return delta.total_seconds()
```

## Core Functions

### JSONL Parser

```python
def parse_session_file(session_id: str) -> list[TraceEvent]:
    """
    Parse JSONL file into tree of TraceEvents

    Input data sources: /Users/gang/.claude/projects/*/*.jsonl
    Output destinations: In-memory TraceEvent tree structure
    Dependencies: json, pathlib
    Key exports: parse_session_file()
    Side effects: Reads files from disk
    """
    file_path = find_session_file(session_id)
    events = []

    with open(file_path) as f:
        for line in f:
            data = json.loads(line)

            # Skip non-trace events
            if data['type'] == 'file-history-snapshot':
                continue

            # Create TraceEvent from JSON
            if data['type'] in ['user', 'assistant', 'system']:
                events.append(TraceEvent.from_json(data))

    # Build tree structure using parent_uuid
    return build_event_tree(events)
```

### Tree Builder

```python
def build_event_tree(events: list[TraceEvent]) -> list[TraceEvent]:
    """
    Convert flat list to tree using parent_uuid relationships

    Algorithm:
    1. Create UUID -> Event mapping
    2. For each event, attach to parent or mark as root
    3. Return list of root events
    """
    event_map = {e.uuid: e for e in events}
    roots = []

    for event in events:
        if event.parent_uuid and event.parent_uuid in event_map:
            # Attach to parent
            event_map[event.parent_uuid].children.append(event)
        else:
            # No parent = root node
            roots.append(event)

    return roots
```

### Project Scanner

```python
def scan_projects() -> list[Project]:
    """
    Scan /Users/gang/.claude/projects/ for all project folders

    Returns list of Project objects with metadata
    """
    projects_dir = Path("/Users/gang/.claude/projects")
    projects = []

    for project_folder in projects_dir.iterdir():
        if not project_folder.is_dir():
            continue

        # Count session files
        session_files = list(project_folder.glob("*.jsonl"))
        if not session_files:
            continue

        # Get last session timestamp
        last_session = max(
            get_session_timestamp(f) for f in session_files)

        # Clean up project name
        name = project_folder.name.replace('-Users-gang-', '') \
                                   .replace('-', ' ').title()

        projects.append(Project(
            name=name,
            path=str(project_folder),
            folder_name=project_folder.name,
            session_count=len(session_files),
            last_session=last_session
        ))

    return sorted(projects, key=lambda p: p.last_session, reverse=True)
```

## UI Components

### TraceTree Component

```python
def TraceTree(events: list[TraceEvent], session_id: str):
    """
    Renders left panel tree structure

    Creates nested navigation with expandable nodes
    """
    return Div(
        NavContainer(
            *[TraceNode(e, level=0, session_id=session_id)
              for e in events],
            cls="trace-tree"),
        cls="trace-tree-container",
        style="width: 40%; height: 100vh; overflow-y: auto; border-right: 1px solid #333;")
```

### TraceNode Component

```python
def TraceNode(event: TraceEvent, level: int, session_id: str, next_sibling: TraceEvent = None):
    """
    Single tree node (recursive for children)

    Displays:
    - Icon based on event type
    - Event label
    - Timestamp
    - Duration to next event (if available)
    - Token count with breakdown (if applicable)
    - Nested children
    """
    icon = get_icon_for_type(event.type)
    label = get_label_for_event(event)
    time_str = event.timestamp.strftime("%H:%M:%S")

    # Calculate duration to next sibling (for response time)
    duration_str = None
    if next_sibling:
        duration = event.duration_to(next_sibling)
        if duration > 0:
            duration_str = Span(f"({duration:.1f}s)",
                              cls="text-xs text-yellow-400 font-semibold")

    # Token display with breakdown
    token_display = None
    if event.token_count > 0:
        breakdown = event.token_breakdown
        # Tooltip with full breakdown
        tooltip = (
            f"Input: {breakdown['input_tokens']} | "
            f"Cache Create: {breakdown['cache_creation_input_tokens']} | "
            f"Cache Read: {breakdown['cache_read_input_tokens']} | "
            f"Output: {breakdown['output_tokens']}"
        )
        token_display = Span(
            f"{breakdown['total_tokens']} tok",
            cls="text-xs text-gray-400",
            title=tooltip)  # Hover to see breakdown

    # Main node content
    node_content = DivHStacked(
        UkIcon(icon, width=16, height=16),
        Span(label, cls="font-medium text-sm"),
        Span(time_str, cls="text-xs text-gray-500"),
        duration_str,  # Duration if available
        token_display,  # Token count if available
        cls="cursor-pointer hover:bg-gray-800 p-2 rounded gap-2",
        hx_get=f"/trace-node/{event.uuid}?session_id={session_id}",
        hx_target="#detail-panel",
        hx_swap="innerHTML")

    # If has children, create nested nav and pass next sibling info
    if event.children:
        children_nodes = []
        for i, child in enumerate(event.children):
            next_child = event.children[i+1] if i+1 < len(event.children) else None
            children_nodes.append(TraceNode(child, level+1, session_id, next_child))

        return NavParentLi(
            node_content,
            NavContainer(*children_nodes, parent=False),
            style=f"margin-left: {level * 20}px")
    else:
        return Li(node_content,
                 style=f"margin-left: {level * 20}px")


def get_icon_for_type(event_type: str) -> str:
    """Map event type to Lucide icon name"""
    icons = {
        'user': 'message-circle',
        'assistant': 'bot',
        'system': 'info',
        'tool_call': 'wrench',
        'tool_result': 'check-circle'
    }
    return icons.get(event_type, 'circle')


def get_label_for_event(event: TraceEvent) -> str:
    """Generate human-readable label for event"""
    if event.type == 'user':
        # Truncate first line of message
        content = event.message.get('content', '')[:50]
        return f"User: {content}..."
    elif event.type == 'assistant':
        if event.tool_calls:
            return f"Assistant ({len(event.tool_calls)} tools)"
        return "Assistant"
    elif event.type == 'system':
        return "System"
    return event.type.title()
```

### DetailPanel Component

```python
def DetailPanel(event: TraceEvent | None, next_event: TraceEvent = None):
    """
    Right panel showing event details in scrollable vertical layout

    Layout (no tabs, everything scrollable):
    1. Metrics section at top (duration, tokens, timing)
    2. Input section (always shown)
    3. Output section (if available, shown below input)
    4. Additional metadata at bottom

    Displays:
    - Metrics (duration, tokens) - AT THE TOP
    - Input content with syntax highlighting
    - Output content with syntax highlighting (below input)
    - Metadata (timestamp, UUID, etc) - AT THE BOTTOM
    - Copy buttons for each section
    - Everything is scrollable vertically (no tabs)
    """
    if not event:
        return Div(
            P("Select an event from the tree to view details",
              cls="text-gray-500 text-center mt-20"),
            id="detail-panel",
            cls="w-3/5 p-6")

    # === METRICS SECTION (AT TOP, like the screenshot) ===
    metrics_section = None
    if event.type == 'assistant' and event.token_count > 0:
        breakdown = event.token_breakdown

        # Calculate duration from previous event (if available)
        duration_display = None
        if next_event:
            duration = event.duration_to(next_event)
            duration_display = f"{duration:.2f}s"

        # Metrics grid (3 columns like screenshot)
        metrics_section = Div(
            H3("📊 Metrics", cls="text-lg font-semibold mb-3"),

            # Row 1: Start time, Duration, Total tokens
            Div(
                Div(
                    Span("Start", cls="text-xs text-gray-500 block"),
                    Span(event.timestamp.strftime("%b %d %I:%M:%S %p"),
                         cls="text-sm font-semibold")),
                Div(
                    Span("Duration", cls="text-xs text-gray-500 block"),
                    Span(duration_display or "N/A", cls="text-sm font-semibold")),
                Div(
                    Span("Total tokens", cls="text-xs text-gray-500 block"),
                    Span(f"{breakdown['total_tokens']:,}", cls="text-sm font-semibold")),
                cls="grid grid-cols-3 gap-4 mb-4"),

            # Row 2: Token breakdown (Prompt tokens, Completion tokens, Total)
            Div(
                Div(
                    Span("Prompt tokens", cls="text-xs text-gray-500 block"),
                    Span(f"{breakdown['input_tokens'] + breakdown['cache_creation_input_tokens'] + breakdown['cache_read_input_tokens']:,}",
                         cls="text-sm font-semibold")),
                Div(
                    Span("Completion tokens", cls="text-xs text-gray-500 block"),
                    Span(f"{breakdown['output_tokens']:,}", cls="text-sm font-semibold")),
                Div(
                    Span("Total tokens", cls="text-xs text-gray-500 block"),
                    Span(f"{breakdown['total_tokens']:,}", cls="text-sm font-semibold")),
                cls="grid grid-cols-3 gap-4 mb-4"),

            # Expandable: Detailed cache breakdown
            Details(
                Summary("Cache Breakdown", cls="cursor-pointer text-xs text-gray-400 hover:text-gray-200"),
                Ul(
                    Li(f"Input Tokens: {breakdown['input_tokens']:,}"),
                    Li(f"Cache Creation: {breakdown['cache_creation_input_tokens']:,}"),
                    Li(f"Cache Read: {breakdown['cache_read_input_tokens']:,}"),
                    Li(f"Output Tokens: {breakdown['output_tokens']:,}"),
                    cls="ml-4 mt-2 text-xs space-y-1"),
                cls="mt-2"),

            cls="p-4 bg-gray-900 rounded mb-4 border border-gray-700")

    # === INPUT & OUTPUT SECTIONS (No tabs, just scrollable vertical layout) ===

    # Input section (always present)
    input_section = Section(
        DivHStacked(
            H3("➡️  Input", cls="text-lg font-bold"),
            Button("Copy", cls="btn-sm",
                  onclick=f"navigator.clipboard.writeText({repr(event.input_content)})")),
        CodeBlock(event.input_content, language="markdown"),
        cls="mb-6")

    # Output section (if assistant message)
    output_section = None
    if event.has_output:
        output_section = Section(
            DivHStacked(
                H3("⬅️  Output", cls="text-lg font-bold"),
                Button("Copy", cls="btn-sm",
                      onclick=f"navigator.clipboard.writeText({repr(event.output_content)})")),
            CodeBlock(event.output_content, language="json"),
            cls="mb-6")

    # === ADDITIONAL METADATA (at bottom) ===
    metadata = Div(
        P(f"⏱️  Timestamp: {event.timestamp.isoformat()}"),
        P(f"🔑 UUID: {event.uuid}"),
        P(f"📋 Session: {event.session_id}") if event.session_id else None,
        P(f"📂 Directory: {event.cwd}") if event.cwd else None,
        P(f"🌿 Branch: {event.git_branch}") if event.git_branch else None,
        cls="text-sm text-gray-400 mt-4 p-4 bg-gray-900 rounded space-y-2")

    return Div(
        metrics_section,  # METRICS AT TOP
        input_section,    # INPUT (always shown)
        output_section,   # OUTPUT (if available) - shown below input
        metadata,         # METADATA AT BOTTOM
        id="detail-panel",
        cls="w-3/5 p-6 overflow-y-auto",
        style="height: 100vh;")


def CodeBlock(content: str, language: str = "text"):
    """Syntax-highlighted code block"""
    return Pre(
        Code(content, cls=f"language-{language}"),
        cls="bg-gray-900 p-4 rounded overflow-x-auto")
```

## Visual Design

### Layout

**Home Page (Accordion View):**

```
┌────────────────────────────────────────────────────────────┐
│  Claude Code Trace Viewer                                  │
├────────────────────────────────────────────────────────────┤
│  ▼ CLIProxyAPI                   4 sessions   Last: 11:11  │
│  ├─ 2025-09-30 11:11  Session about...       [15 msgs] →  │
│  ├─ 2025-09-30 10:58  Model setup...         [10 msgs] →  │
│  ├─ 2025-09-30 10:54  Bug fix...             [75 msgs] →  │
│  └─ 2025-09-30 10:38  Initial setup...        [3 msgs] →  │
├────────────────────────────────────────────────────────────┤
│  ► RAG Course Practice          21 sessions   Last: 18:22  │
├────────────────────────────────────────────────────────────┤
│  ► Personal Bizos              100 sessions   Last: 11:01  │
├────────────────────────────────────────────────────────────┤
│  ► Other Projects...                                       │
└────────────────────────────────────────────────────────────┘
```

**Two-Panel Design (Scrollable Vertical Layout):**

````
┌──────────────────────────────────────────────────────────────────────┐
│  Trace Tree (40%)         │  Detail Panel (60%) - All Scrollable     │
│                            │                                          │
│  📝 user - 10:39:34 (3.6s) │  📊 Metrics                             │
│    └─ 🤖 assistant         │  ┌──────────────────────────────────┐  │
│        10:39:38            │  │ Start        Duration  Total tok │  │
│        24,180 tok          │  │ Feb 19 10:08 16.04s    2,241    │  │
│        ├─ 🔧 Read (0.3s)   │  │ Prompt tok   Completion  Total  │  │
│        │   └─ ✓ result     │  │ 694          1,547       2,241  │  │
│        └─ 🔧 Grep (0.2s)   │  └──────────────────────────────────┘  │
│            └─ ✓ result     │                                          │
│                            │  ➡️  Input                [Copy]         │
│  📝 user - 10:40:12 (4.2s) │  ┌──────────────────────────────────┐  │
│    └─ 🤖 assistant         │  │ ```markdown                      │  │
│        10:40:16            │  │ User message content here...     │  │
│        1,661 tok           │  │ ```                              │  │
│                            │  └──────────────────────────────────┘  │
│                            │                                          │
│  [scrollable]              │  ⬅️  Output               [Copy]         │
│                            │  ┌──────────────────────────────────┐  │
│                            │  │ ```json                          │  │
│                            │  │ { "type": "text",                │  │
│                            │  │   "content": "Response..." }     │  │
│                            │  │ ```                              │  │
│                            │  └──────────────────────────────────┘  │
│                            │                                          │
│                            │  ⏱️  Timestamp: 2025-09-30T02:39:34Z    │
│                            │  🔑 UUID: abc-123-def                   │
│                            │                                          │
│                            │  [scroll for more...]                    │
└──────────────────────────────────────────────────────────────────────┘
````

**Visual Elements:**

- **No tabs**: Input and Output shown sequentially in vertical scroll
- **Timestamps**: Gray text showing `HH:MM:SS`
- **Durations**: Yellow text in parentheses `(3.6s)`
- **Token counts**: Gray text, hover shows breakdown tooltip
- **Icons**: Lucide icons for event types
- **Layout**: Metrics → Input → Output → Metadata (all scrollable)

### Styling

**Dark Theme:**

- Background: `#1a1a1a` (dark gray)
- Text: `#e5e5e5` (light gray)
- Borders: `#333` (medium gray)
- Hover: `#2a2a2a` (slightly lighter)

**Color Coding:**

- **Timestamps**: `#9ca3af` (gray-400) - subtle, secondary info
- **Durations**: `#fbbf24` (yellow-400) - highlighted, attention-grabbing
- **Token counts**: `#9ca3af` (gray-400) - with yellow highlight on hover
- **Token breakdown**: `#fbbf24` (yellow-400) for heading, white for values

**Tree Indentation:**

```css
.trace-tree li {
  padding-left: 20px;
  border-left: 1px solid #333;
}

.trace-tree li:hover {
  background-color: #2a2a2a;
}
```

**Syntax Highlighting:**

- Use Prism.js or Highlight.js
- Include via CDN in FastHTML `hdrs` parameter
- Dark theme: `prism-tomorrow` or `atom-one-dark`

### Icons

Using Lucide icons via `UkIcon` from MonsterUI:

- `message-circle` - User messages
- `bot` - Assistant responses
- `wrench` - Tool calls
- `check-circle` - Tool results
- `info` - System messages
- `folder` - Projects
- `file-text` - Sessions

## Dependencies

### requirements.txt

```
python-fasthtml>=0.6.0
monsterui>=0.1.0
python-dateutil>=2.8.0
```

### Installation

```bash
pip install python-fasthtml monsterui python-dateutil
```

## Running the Application

### Development Mode

```bash
cd /Users/gang/claude-trace-viewer
python app.py
```

Visit: `http://localhost:5001`

### Configuration

Default settings in `app.py`:

```python
PROJECTS_DIR = Path("/Users/gang/.claude/projects")
PORT = 5001
DEBUG = True
```

## User Flow

### Complete User Journey

**1. Start the Viewer**

```bash
cd /Users/gang/claude-trace-viewer
python app.py
# Opens http://localhost:5001
```

**2. Home Page - See All Projects & Sessions (Single Page)**

- View accordion list of all projects
- Click project header to expand/collapse sessions
- Sessions sorted by recency (newest first)
- Click any session row to open trace viewer

**3. Trace Viewer Page - Two-Panel Layout**

- **Top**: Session Context Panel
  - Claude Code version
  - Timestamp
  - Working directory
  - Git branch
  - [View CLAUDE.md] buttons
  - Git command helper
- **Left Panel**: Trace Tree (40%)
  - Click nodes to select events
  - Expandable tree structure
- **Right Panel**: Detail View (60%)
  - Shows selected event details
  - Input/Output tabs
  - Syntax highlighting
  - Metadata display

**4. View Session Context**

- Click **[View Global CLAUDE.md]** → Modal with current global CLAUDE.md
- Click **[View Project CLAUDE.md]** → Modal with current project CLAUDE.md
- Click **[Copy Command]** → Copy git log command
- Run command in terminal → Find commit hash
- Use commit hash → View CLAUDE.md at that exact time

**5. Navigate Back**

- Browser back button → Returns to home page
- Or click home link (if added)

### Key User Actions

| Action                 | Result                              |
| ---------------------- | ----------------------------------- |
| Click project header   | Expands/collapses sessions          |
| Click session row      | Opens trace viewer                  |
| Click trace tree node  | Updates detail panel                |
| Click [View CLAUDE.md] | Shows modal with current CLAUDE.md  |
| Click [Copy Command]   | Copies git log command to clipboard |
| Browser back           | Returns to previous page            |

## Implementation Checklist

- [ ] Create project structure (`app.py`, `models.py`, `components.py`)
- [ ] Install dependencies (`requirements.txt`)
- [ ] Implement data models (Project, Session, TraceEvent)
- [ ] Build JSONL parser (`parse_session_file()`)
- [ ] Build tree builder (`build_event_tree()`)
- [ ] Implement project scanner (`scan_projects()`)
- [ ] Create FastHTML app with routes:
  - [ ] `/` - Home page (accordion with projects + sessions)
  - [ ] `/toggle-project/{project_name}` - HTMX endpoint to expand/collapse
  - [ ] `/session/{session_id}` - Trace viewer
  - [ ] `/trace-node/{uuid}` - HTMX detail endpoint
- [ ] Build UI components:
  - [ ] `ProjectAccordion` - Expandable project section
  - [ ] `SessionList` - List of sessions (sorted by recency)
  - [ ] `SessionRow` - Individual session row
  - [ ] `TraceTree` - Left panel tree structure
  - [ ] `TraceNode` - Single tree node (recursive)
  - [ ] `DetailPanel` - Right panel detail view
  - [ ] `CodeBlock` - Syntax highlighted code
- [ ] Add custom CSS (`static/custom.css`)
- [ ] Add syntax highlighting (Prism.js)
- [ ] Test with real session files
- [ ] Add error handling and edge cases
- [ ] Polish UI and styling

## Future Enhancements

- **Search/Filter**: Full-text search across sessions
- **Export**: Export trace as JSON, Markdown, or HTML
- **Stats Dashboard**: Session statistics, token usage over time
- **Dark/Light Mode Toggle**: User preference
- **Keyboard Shortcuts**: Navigate tree with arrow keys
- **Real-time Updates**: Watch for new sessions (file system monitoring)
- **Diff View**: Compare two sessions side-by-side
- **Bookmarks**: Mark important sessions
- **Tags**: User-defined tags for sessions
