"""
Claude Code trace viewer application that displays session traces from JSONL files.

This application automatically detects the current user's Claude Code sessions and
displays them in a web interface with accurate local timezone conversions.

Input data sources: JSONL files in ~/.claude/projects/ (auto-detected for current user)
Output destinations: Web UI served at http://localhost:5001
Dependencies: FastHTML, MonsterUI, python-dateutil
Key exports: app, serve()
Side effects: Reads session files from user's home directory, serves HTTP server

Usage:
    python main.py
    # or with uv:
    uv run python main.py

The app will automatically:
- Detect the current user's home directory
- Find Claude Code sessions in ~/.claude/projects/
- Convert UTC timestamps to local timezone for accurate relative time display
"""

from fasthtml.common import *
from monsterui.all import *
from pathlib import Path
from datetime import datetime
from dateutil import parser as date_parser
import json
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any

# App setup
custom_css = Style(
    """
    .trace-event {
        cursor: pointer;
        padding: 0.5rem;
        transition: all 0.2s ease;
        border-radius: 0.375rem;
        border-left: 3px solid transparent;
    }

    .trace-event:hover {
        background-color: rgb(31, 41, 55);
    }

    .trace-event.selected {
        background-color: rgb(17, 24, 39);
        border-left-color: rgb(59, 130, 246);
    }
"""
)

selection_script = Script(
    """
    document.addEventListener('DOMContentLoaded', function() {
        document.body.addEventListener('htmx:beforeRequest', function(evt) {
            if (evt.detail.elt.classList.contains('trace-event')) {
                document.querySelectorAll('.trace-event').forEach(function(item) {
                    item.classList.remove('selected');
                });
                evt.detail.elt.classList.add('selected');
            }
        });
    });
"""
)

app, rt = fast_app(hdrs=[*Theme.blue.headers(), custom_css, selection_script])


# Data models
@dataclass
class TraceEvent:
    """Single trace event from JSONL file"""

    id: str  # uuid from JSONL
    event_type: str  # type field (user, assistant, system, summary)
    timestamp: str
    data: Dict[str, Any]  # Full event data
    parent_id: Optional[str] = None  # parentUuid from JSONL
    children: List["TraceEvent"] = field(default_factory=list)
    level: int = 0

    def get_display_text(self) -> str:
        """Get human-readable text for display"""
        # For summary type
        if self.event_type == "summary":
            return self.data.get("summary", "")

        # For user/assistant messages
        if "message" in self.data:
            msg = self.data["message"]
            if isinstance(msg.get("content"), str):
                return msg["content"][:200]  # Truncate long messages
            elif isinstance(msg.get("content"), list):
                # Handle content array (tool uses, etc)
                for item in msg["content"]:
                    if isinstance(item, dict):
                        if item.get("type") == "text":
                            return item.get("text", "")[:200]
                        elif item.get("type") == "tool_use":
                            return f"Tool: {item.get('name', 'unknown')}"
                return "Multiple content items"

        # For system events
        if self.event_type == "system":
            return self.data.get("content", "")[:200]

        return f"{self.event_type} event"


@dataclass
class Session:
    """Session metadata and trace events"""

    session_id: str
    project_name: str
    created_at: datetime
    file_path: Path
    trace_tree: List[TraceEvent] = field(default_factory=list)


# Session discovery and parsing
def get_sessions_dir() -> Path:
    """Get Claude projects directory"""
    return Path.home() / ".claude" / "projects"


def discover_sessions() -> List[Session]:
    """Discover all session files from project directories"""
    projects_dir = get_sessions_dir()
    if not projects_dir.exists():
        return []

    sessions = []
    # Iterate through project directories
    for project_dir in projects_dir.iterdir():
        if not project_dir.is_dir() or project_dir.name.startswith("."):
            continue

        # Extract project name from directory name (format: -Users-gang-project-name)
        project_name = project_dir.name.replace("-", "/")

        # Find all JSONL files in project directory
        for session_file in project_dir.glob("*.jsonl"):
            session_id = session_file.stem

            # Parse file to get last timestamp (most recent activity)
            try:
                created_at = None
                with open(session_file, "r") as f:
                    # Read through all lines to find the last event with timestamp
                    for line in f:
                        if not line.strip():
                            continue
                        try:
                            event = json.loads(line)
                            timestamp_str = event.get("timestamp", "")
                            if timestamp_str:
                                # Keep updating to get the LAST timestamp
                                created_at = date_parser.parse(timestamp_str)
                                # Convert to local time (naive datetime)
                                if created_at.tzinfo is not None:
                                    # Convert UTC to local time
                                    created_at = created_at.astimezone().replace(
                                        tzinfo=None
                                    )
                        except Exception:
                            continue

                # Skip sessions with no timestamp (summary-only sessions)
                if created_at is None:
                    continue

                sessions.append(
                    Session(
                        session_id=session_id,
                        project_name=project_name,
                        created_at=created_at,
                        file_path=session_file,
                    )
                )
            except Exception as e:
                print(f"Error parsing {session_file}: {e}")
                continue

    return sorted(sessions, key=lambda s: s.created_at, reverse=True)


def parse_session_file(file_path: Path) -> List[TraceEvent]:
    """Parse JSONL file as flat timeline (not tree)"""
    events = []

    with open(file_path, "r") as f:
        for idx, line in enumerate(f):
            if not line.strip():
                continue

            try:
                data = json.loads(line)
                event = TraceEvent(
                    id=data.get("uuid", str(idx)),
                    event_type=data.get("type", "unknown"),
                    timestamp=data.get("timestamp", ""),
                    data=data,
                    parent_id=data.get("parentUuid"),
                )
                events.append(event)
            except Exception as e:
                print(f"Error parsing line {idx}: {e}")
                continue

    # Return as flat list (no tree structure for conversation view)
    # All events at level 0
    return events


def group_sessions_by_project(sessions: List[Session]) -> Dict[str, List[Session]]:
    """Group sessions by project name"""
    projects = {}
    for session in sessions:
        if session.project_name not in projects:
            projects[session.project_name] = []
        projects[session.project_name].append(session)
    return projects


# Helper functions
def get_relative_time(dt: datetime) -> str:
    """Convert datetime to relative time string (e.g., '2 days ago')"""
    now = datetime.now()
    diff = now - dt

    seconds = diff.total_seconds()

    if seconds < 60:
        return "just now"
    elif seconds < 3600:
        minutes = int(seconds / 60)
        return f"{minutes} minute{'s' if minutes != 1 else ''} ago"
    elif seconds < 86400:
        hours = int(seconds / 3600)
        return f"{hours} hour{'s' if hours != 1 else ''} ago"
    elif seconds < 604800:
        days = int(seconds / 86400)
        return f"{days} day{'s' if days != 1 else ''} ago"
    elif seconds < 2592000:
        weeks = int(seconds / 604800)
        return f"{weeks} week{'s' if weeks != 1 else ''} ago"
    elif seconds < 31536000:
        months = int(seconds / 2592000)
        return f"{months} month{'s' if months != 1 else ''} ago"
    else:
        years = int(seconds / 31536000)
        return f"{years} year{'s' if years != 1 else ''} ago"


# UI Components
def ProjectAccordion(project_name: str, sessions: List[Session]):
    """Accordion item for a project with its sessions"""
    session_items = []
    for session in sessions:
        relative_time = get_relative_time(session.created_at)
        session_items.append(
            Li(
                A(
                    DivFullySpaced(
                        Span(session.session_id, cls=TextT.bold),
                        Span(relative_time, cls=TextT.muted + " " + TextT.sm),
                    ),
                    href=f"/viewer/{session.session_id}",
                    cls="hover:bg-gray-100 p-2 rounded block",
                )
            )
        )

    return Li(
        A(project_name, cls="uk-accordion-title font-bold"),
        Div(Ul(*session_items, cls="space-y-1 mt-2"), cls="uk-accordion-content"),
    )


def TraceTreeNode(event: TraceEvent, session_id: str):
    """Flat timeline event node"""
    node_id = f"node-{event.id}"

    display_text = event.get_display_text()

    # Format timestamp nicely
    timestamp_display = None
    if event.timestamp:
        try:
            dt = date_parser.parse(event.timestamp)
            timestamp_display = dt.strftime("%H:%M:%S")
        except Exception:
            timestamp_display = event.timestamp

    return DivLAligned(
        UkIcon("circle", width=16, height=16),
        Span(f"{event.event_type}", cls="text-xs text-gray-500 ml-2"),
        Span(display_text, cls=TextT.bold + " ml-2"),
        (
            Span(timestamp_display, cls=TextT.muted + " " + TextT.sm + " ml-4")
            if timestamp_display
            else None
        ),
        cls="trace-event",
        hx_get=f"/event/{session_id}/{event.id}",
        hx_target="#detail-panel",
        id=node_id,
    )


def DetailPanel(event: TraceEvent):
    """Detail panel showing event data"""
    formatted_json = json.dumps(event.data, indent=2)

    return Div(
        H3(f"Event: {event.event_type}", cls="mb-4"),
        P(f"Timestamp: {event.timestamp}", cls=TextT.muted + " mb-2"),
        P(f"ID: {event.id}", cls=TextT.muted + " mb-4"),
        H4("Event Data:", cls="mb-2"),
        Pre(
            Code(formatted_json),
            cls="bg-gray-900 text-gray-100 p-4 rounded overflow-auto text-sm",
        ),
        cls="p-4",
    )


def Layout(content):
    """Main layout wrapper"""
    return Container(
        DivCentered(H1("Claude Code Trace Viewer", cls="my-8"), cls="border-b pb-4"),
        content,
        cls="min-h-screen",
    )


# Routes
@rt
def index():
    """Home page with project accordion"""
    sessions = discover_sessions()

    if not sessions:
        return Layout(
            Card(
                P("No session files found in ~/.claude/sessions/", cls=TextT.muted),
                cls="mt-8",
            )
        )

    projects = group_sessions_by_project(sessions)

    accordion_items = [
        ProjectAccordion(project_name, project_sessions)
        for project_name, project_sessions in sorted(projects.items())
    ]

    return Layout(
        Div(
            H2("Projects & Sessions", cls="mb-4"),
            Ul(
                *accordion_items, cls="uk-accordion", data_uk_accordion="multiple: true"
            ),
            cls="mt-8",
        )
    )


@rt("/viewer/{session_id}")
def viewer(session_id: str):
    """Trace viewer page with tree and detail panel"""
    # Find session file in project directories
    sessions = discover_sessions()
    session_file = None
    for session in sessions:
        if session.session_id == session_id:
            session_file = session.file_path
            break

    if not session_file or not session_file.exists():
        return Layout(
            Card(
                P(f"Session file not found: {session_id}", cls=TextT.muted), cls="mt-8"
            )
        )

    trace_tree = parse_session_file(session_file)

    tree_nodes = [TraceTreeNode(event, session_id) for event in trace_tree]

    return Layout(
        Div(
            DivFullySpaced(
                H2(f"Session: {session_id[:16]}...", cls="mb-4"),
                A("← Back to Home", href="/", cls=AT.primary),
                cls="mb-4",
            ),
            Grid(
                # Left panel - Trace tree
                Div(
                    Card(
                        H3("Trace Tree", cls="mb-4 font-bold"),
                        Div(
                            *(
                                tree_nodes
                                if tree_nodes
                                else [P("No trace events found", cls=TextT.muted)]
                            ),
                            cls="overflow-auto",
                            style="max-height: 70vh",
                        ),
                        cls="p-4",
                    )
                ),
                # Right panel - Detail view
                Div(
                    Card(
                        H3("Event Details", cls="mb-4 font-bold"),
                        Div(
                            P("Select an event to view details", cls=TextT.muted),
                            id="detail-panel",
                            cls="overflow-auto",
                            style="max-height: 70vh",
                        ),
                        cls="p-4",
                    )
                ),
                cols=2,
                cls="gap-4 mt-4",
            ),
        )
    )


@rt("/event/{session_id}/{id}")
def event(session_id: str, id: str):
    """Get event details (for HTMX)"""
    # Find session file in project directories
    sessions = discover_sessions()
    session_file = None
    for session in sessions:
        if session.session_id == session_id:
            session_file = session.file_path
            break

    if not session_file or not session_file.exists():
        return Div(
            P("Session file not found", cls=TextT.muted),
            cls="p-4",
        )

    # Parse session and find event
    trace_tree = parse_session_file(session_file)

    def find_event(events: List[TraceEvent], event_id: str) -> Optional[TraceEvent]:
        for event in events:
            if event.id == event_id:
                return event
            if event.children:
                found = find_event(event.children, event_id)
                if found:
                    return found
        return None

    found_event = find_event(trace_tree, id)

    if not found_event:
        return Div(
            P(f"Event {id} not found", cls=TextT.muted),
            cls="p-4",
        )

    return DetailPanel(found_event)


# Start server
serve()
