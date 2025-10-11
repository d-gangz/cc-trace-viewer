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
        line-height: 1.5;
        word-wrap: break-word;
    }

    .trace-event > span:last-child {
        display: -webkit-box;
        -webkit-line-clamp: 2;
        -webkit-box-orient: vertical;
        overflow: hidden;
    }

    .trace-event:hover {
        background-color: rgb(31, 41, 55);
    }

    .trace-event.selected {
        background-color: rgb(17, 24, 39);
        border-left-color: rgb(59, 130, 246);
    }

    .trace-event-sidechain {
        padding-left: 16px;
        border-left: 2px solid rgb(107, 114, 128);
        margin-left: 8px;
        border-radius: 0;
    }

    .trace-event-sidechain.selected {
        border-left-color: rgb(59, 130, 246);
    }
"""
)

selection_script = Script(
    """
    document.addEventListener('DOMContentLoaded', function() {
        // Auto-select first trace event on page load
        setTimeout(function() {
            var events = document.querySelectorAll('.trace-event');
            if (events.length > 0) {
                htmx.trigger(events[0], 'click');
            }
        }, 100);

        // Handle selection on HTMX request
        document.body.addEventListener('htmx:beforeRequest', function(evt) {
            if (evt.detail.elt.classList.contains('trace-event')) {
                document.querySelectorAll('.trace-event').forEach(function(item) {
                    item.classList.remove('selected');
                });
                evt.detail.elt.classList.add('selected');
            }
        });

        // Handle keyboard navigation
        document.addEventListener('keydown', function(evt) {
            if (evt.key !== 'ArrowUp' && evt.key !== 'ArrowDown') {
                return;
            }

            evt.preventDefault();

            var events = Array.from(document.querySelectorAll('.trace-event'));
            if (events.length === 0) return;

            var selected = document.querySelector('.trace-event.selected');
            var currentIndex = selected ? events.indexOf(selected) : -1;
            var newIndex;

            if (evt.key === 'ArrowDown') {
                newIndex = currentIndex + 1;
                if (newIndex >= events.length) newIndex = 0;
            } else {
                newIndex = currentIndex - 1;
                if (newIndex < 0) newIndex = events.length - 1;
            }

            // Trigger HTMX on new element
            htmx.trigger(events[newIndex], 'click');

            // Scroll into view
            events[newIndex].scrollIntoView({ behavior: 'smooth', block: 'nearest' });
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
    is_sidechain: bool = False  # isSidechain from JSONL

    def is_tool_call(self) -> bool:
        """Check if this event is a tool call"""
        if "message" in self.data:
            msg = self.data["message"]
            if isinstance(msg.get("content"), list):
                for item in msg["content"]:
                    if isinstance(item, dict) and item.get("type") == "tool_use":
                        return True
        return False

    def is_tool_result(self) -> bool:
        """Check if this event is a tool result"""
        if "message" in self.data:
            msg = self.data["message"]
            if isinstance(msg.get("content"), list):
                for item in msg["content"]:
                    if isinstance(item, dict) and item.get("type") == "tool_result":
                        return True
        return False

    def get_tool_use_id(self) -> Optional[str]:
        """Get tool_use_id from tool_result"""
        if "message" in self.data:
            msg = self.data["message"]
            if isinstance(msg.get("content"), list):
                for item in msg["content"]:
                    if isinstance(item, dict) and item.get("type") == "tool_result":
                        return item.get("tool_use_id")
        return None

    def get_tool_name(self) -> str:
        """Get tool name if this is a tool call"""
        if "message" in self.data:
            msg = self.data["message"]
            if isinstance(msg.get("content"), list):
                for item in msg["content"]:
                    if isinstance(item, dict) and item.get("type") == "tool_use":
                        return item.get("name", "unknown")
        return ""

    def is_thinking(self) -> bool:
        """Check if this event contains thinking content"""
        if "message" in self.data:
            msg = self.data["message"]
            if isinstance(msg.get("content"), list):
                for item in msg["content"]:
                    if isinstance(item, dict) and item.get("type") == "thinking":
                        return True
        return False

    def get_thinking_text(self) -> str:
        """Get thinking text from message content"""
        if "message" in self.data:
            msg = self.data["message"]
            if isinstance(msg.get("content"), list):
                for item in msg["content"]:
                    if isinstance(item, dict) and item.get("type") == "thinking":
                        return item.get("thinking", "")
        return ""

    def calculate_duration(
        self, previous_event: Optional["TraceEvent"], all_events: List["TraceEvent"]
    ) -> Optional[float]:
        """
        Calculate duration in seconds for this event.

        For thinking/assistant/tool_call: duration = this.timestamp - previous.timestamp
        For tool_result: duration = this.timestamp - matching_tool_use.timestamp

        Returns duration in seconds or None if cannot calculate
        """
        # Parse this event's timestamp
        try:
            current_time = date_parser.parse(self.timestamp)
        except Exception:
            return None

        # For tool results, find the matching tool_use event
        if self.is_tool_result():
            tool_use_id = self.get_tool_use_id()
            if tool_use_id and all_events:
                # Find the tool_use event with matching ID
                for event in all_events:
                    if "message" in event.data:
                        msg = event.data["message"]
                        if isinstance(msg.get("content"), list):
                            for item in msg["content"]:
                                if (
                                    isinstance(item, dict)
                                    and item.get("type") == "tool_use"
                                    and item.get("id") == tool_use_id
                                ):
                                    # Found matching tool_use, calculate duration
                                    try:
                                        tool_use_time = date_parser.parse(
                                            event.timestamp
                                        )
                                        duration = (
                                            current_time - tool_use_time
                                        ).total_seconds()
                                        return duration
                                    except Exception:
                                        return None
            return None

        # For thinking/assistant/tool_call: use previous event
        if previous_event:
            try:
                previous_time = date_parser.parse(previous_event.timestamp)
                duration = (current_time - previous_time).total_seconds()
                return duration
            except Exception:
                return None

        return None

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
                            return item.get("name", "unknown")
                        elif item.get("type") == "tool_result":
                            # Will be set by TraceTreeNode with proper lookup
                            return "tool_result"
                        elif item.get("type") == "thinking":
                            # Return first 2 lines of thinking text
                            thinking_text = item.get("thinking", "")
                            lines = thinking_text.split("\n")
                            return "\n".join(lines[:2])
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
                    is_sidechain=data.get("isSidechain", False),
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
                        Span(relative_time, cls="text-gray-500 font-normal"),
                    ),
                    href=f"/viewer/{session.session_id}",
                    cls="hover:bg-gray-800 p-2 rounded block",
                )
            )
        )

    # Get most recent session timestamp for this project
    most_recent = max(sessions, key=lambda s: s.created_at)
    project_time = get_relative_time(most_recent.created_at)

    return Li(
        A(
            DivFullySpaced(
                Span(project_name),
                Span(project_time, cls="text-gray-500 font-normal"),
            ),
            cls="uk-accordion-title font-bold",
        ),
        Div(Ul(*session_items, cls="space-y-1 mt-2"), cls="uk-accordion-content"),
    )


def TraceTreeNode(
    event: TraceEvent,
    session_id: str,
    all_events: Optional[List[TraceEvent]] = None,
    previous_event: Optional[TraceEvent] = None,
):
    """Flat timeline event node"""
    node_id = f"node-{event.id}"

    display_text = event.get_display_text()

    # Calculate duration for non-user events (but include tool_result which has type "user")
    duration = None
    if event.event_type != "user" or event.is_tool_result():
        duration = event.calculate_duration(previous_event, all_events or [])

    # Check if this is a thinking event
    if event.is_thinking():
        label = "thinking"
        label_color = "text-xs text-blue-500"
    # Check if this is a tool call
    elif event.is_tool_call():
        # Get the tool call ID and extract last 4 characters
        tool_id = None
        tool_name = None
        subagent_type = None

        if "message" in event.data:
            msg = event.data["message"]
            if isinstance(msg.get("content"), list):
                for item in msg["content"]:
                    if isinstance(item, dict) and item.get("type") == "tool_use":
                        tool_id = item.get("id", "")
                        tool_name = item.get("name", "")
                        # Check if this is a Task tool (subagent)
                        if tool_name == "Task":
                            input_data = item.get("input", {})
                            subagent_type = input_data.get("subagent_type", "")
                        break

        # Handle Task tool (subagent) differently
        if tool_name == "Task" and subagent_type:
            # Change display text to show the subagent name
            display_text = subagent_type

            label = "tool call"
            if tool_id and len(tool_id) >= 4:
                last_4 = tool_id[-4:]
                label = Span(
                    Span("subagent ", cls="text-xs text-cyan-500"),
                    Span(last_4, cls="text-xs text-gray-500 font-normal"),
                )
            else:
                label = Span("subagent", cls="text-xs text-cyan-500")
            label_color = None  # Already set in label
        else:
            # Regular tool call
            label = "tool call"
            if tool_id and len(tool_id) >= 4:
                last_4 = tool_id[-4:]
                label = Span(
                    Span("tool call ", cls="text-xs text-yellow-500"),
                    Span(last_4, cls="text-xs text-gray-500 font-normal"),
                )
            else:
                label = Span("tool call", cls="text-xs text-yellow-500")
            label_color = None  # Already set in label
    elif event.is_tool_result():
        # Get tool_use_id and extract last 4 characters
        tool_use_id = event.get_tool_use_id()

        label = "tool result"
        if tool_use_id and len(tool_use_id) >= 4:
            last_4 = tool_use_id[-4:]
            label = Span(
                Span("tool result ", cls="text-xs text-green-500"),
                Span(last_4, cls="text-xs text-gray-500 font-normal"),
            )
        else:
            label = Span("tool result", cls="text-xs text-green-500")
        label_color = None  # Already set in label

        # Find the corresponding tool_use event to get the tool name for display_text
        if tool_use_id and all_events:
            for e in all_events:
                # Check if this event has a tool_use with matching id
                if "message" in e.data:
                    msg = e.data["message"]
                    if isinstance(msg.get("content"), list):
                        for item in msg["content"]:
                            if (
                                isinstance(item, dict)
                                and item.get("type") == "tool_use"
                            ):
                                if item.get("id") == tool_use_id:
                                    display_text = item.get("name", "unknown")
                                    break
    elif event.event_type == "assistant":
        label = "assistant"
        label_color = "text-xs text-purple-500"
    else:
        label = event.event_type
        label_color = "text-xs text-gray-500"

    # Format duration text (no space between number and unit)
    duration_text = ""
    if duration is not None:
        duration_text = f"{duration:.2f}s"

    # Create eyebrow with label and optional duration (spaced between)
    # label is either a string (with label_color) or a Span element (already styled)
    if isinstance(label, str):
        eyebrow_content = [Span(label, cls=label_color)]
    else:
        eyebrow_content = [label]

    if duration_text:
        eyebrow_content.append(Span(duration_text, cls="text-xs text-gray-500"))

    # Build CSS classes for sidechain events
    css_classes = "trace-event"
    if event.is_sidechain:
        css_classes += " trace-event-sidechain"

    return Div(
        Div(*eyebrow_content, cls="flex justify-between"),
        Span(display_text),
        cls=css_classes,
        hx_get=f"/event/{session_id}/{event.id}",
        hx_target="#detail-panel",
        id=node_id,
    )


def render_markdown_content(text: str):
    """Render text as markdown (simple version - can be enhanced)"""
    # For now, return as pre-formatted text with word wrap
    return Div(
        text,
        cls="whitespace-pre-wrap break-words",
    )


def render_usage_metrics(usage_data: Dict[str, Any], duration: Optional[float] = None):
    """Render usage metrics section"""
    if not usage_data and duration is None:
        return None

    metrics_items = []

    # Add duration as first metric if available (no space between number and unit)
    if duration is not None:
        metrics_items.append(
            Div(
                Span("Duration: ", cls="text-gray-400"),
                Span(f"{duration:.2f}s", cls="text-white"),
                cls="mb-1",
            )
        )

    # Add usage metrics
    if usage_data:
        for key, value in usage_data.items():
            metrics_items.append(
                Div(
                    Span(f"{key}: ", cls="text-gray-400"),
                    Span(str(value), cls="text-white"),
                    cls="mb-1",
                )
            )

    return Div(
        H4("Metrics", cls="mb-2 font-bold"),
        Div(
            *metrics_items,
            cls="mb-4 p-3 bg-gray-800 rounded",
        ),
    )


def DetailPanel(
    event: TraceEvent,
    all_events: Optional[List[TraceEvent]] = None,
    previous_event: Optional[TraceEvent] = None,
):
    """Detail panel showing event data"""
    components = []

    # Calculate duration for non-user events (but include tool_result which has type "user")
    duration = None
    if (event.event_type != "user" or event.is_tool_result()) and all_events:
        duration = event.calculate_duration(previous_event, all_events)

    # Check if event has message content
    if "message" in event.data:
        msg = event.data["message"]
        content = msg.get("content")
        usage = msg.get("usage")  # Usage is inside message object

        if isinstance(content, list):
            # Add metrics section if usage or duration exists
            if usage or duration is not None:
                metrics = render_usage_metrics(usage, duration)
                if metrics:
                    components.append(metrics)

            # Add Content section header
            components.append(H4("Content", cls="mb-2 font-bold"))

            for idx, item in enumerate(content):
                if not isinstance(item, dict):
                    continue

                item_type = item.get("type")

                # Scenario A: text type
                if item_type == "text":
                    text_content = item.get("text", "")
                    components.append(
                        Div(
                            render_markdown_content(text_content),
                            cls="mb-4 p-3 bg-gray-800 rounded",
                        )
                    )

                # Scenario D: thinking type
                elif item_type == "thinking":
                    thinking_text = item.get("thinking", "")
                    components.append(
                        Div(
                            render_markdown_content(thinking_text),
                            cls="mb-4 p-3 bg-gray-800 rounded",
                        )
                    )

                # Scenario A2: image type (in user messages)
                elif item_type == "image":
                    source = item.get("source", {})
                    if isinstance(source, dict):
                        data = source.get("data", "")
                        media_type = source.get("media_type", "image/png")
                        source_type = source.get("type", "base64")

                        if data and source_type == "base64":
                            components.append(
                                Div(
                                    Img(
                                        src=f"data:{media_type};base64,{data}",
                                        alt="User uploaded image",
                                        cls="max-w-full h-auto rounded",
                                        style="max-height: 600px;",
                                    ),
                                    cls="mb-4 p-3 bg-gray-800 rounded",
                                )
                            )

                # Scenario B: tool_use type
                elif item_type == "tool_use":
                    components.append(
                        Div(
                            Div(
                                Span("ID: ", cls="text-gray-400"),
                                Span(item.get("id", ""), cls="text-white break-all"),
                                cls="mb-2",
                            ),
                            Div(
                                Span("Name: ", cls="text-gray-400"),
                                Span(item.get("name", ""), cls="text-white"),
                                cls="mb-2",
                            ),
                            Div(
                                Span("Input: ", cls="text-gray-400"),
                                Pre(
                                    Code(json.dumps(item.get("input", {}), indent=2)),
                                    cls="text-white text-sm whitespace-pre-wrap break-words mt-1",
                                ),
                            ),
                            cls="mb-4 p-3 bg-gray-800 rounded",
                        )
                    )

                # Scenario C: tool_result type
                elif item_type == "tool_result":
                    tool_result_components = []

                    # Get tool_use_id and find the tool name
                    tool_use_id = item.get("tool_use_id")
                    tool_name = "unknown"

                    # Look for the corresponding tool_use event to get the tool name
                    # Search through all events (same logic as TraceTreeNode)
                    if tool_use_id and all_events:
                        for e in all_events:
                            if "message" in e.data:
                                e_msg = e.data["message"]
                                if isinstance(e_msg.get("content"), list):
                                    for check_item in e_msg["content"]:
                                        if (
                                            isinstance(check_item, dict)
                                            and check_item.get("type") == "tool_use"
                                        ):
                                            if check_item.get("id") == tool_use_id:
                                                tool_name = check_item.get(
                                                    "name", "unknown"
                                                )
                                                break
                            if tool_name != "unknown":
                                break

                    # Add tool ID and name
                    tool_result_components.append(
                        Div(
                            Span("Tool ID: ", cls="text-gray-400"),
                            Span(tool_use_id or "N/A", cls="text-white break-all"),
                            cls="mb-2",
                        )
                    )
                    tool_result_components.append(
                        Div(
                            Span("Tool Name: ", cls="text-gray-400"),
                            Span(tool_name, cls="text-white"),
                            cls="mb-2",
                        )
                    )

                    # Display content if exists
                    tool_content = item.get("content")
                    if tool_content:
                        if isinstance(tool_content, str):
                            tool_result_components.append(
                                Div(render_markdown_content(tool_content), cls="mt-2")
                            )
                        elif isinstance(tool_content, list):
                            for content_item in tool_content:
                                if isinstance(content_item, dict):
                                    content_type = content_item.get("type")

                                    if content_type == "text":
                                        tool_result_components.append(
                                            Div(
                                                render_markdown_content(
                                                    content_item.get("text", "")
                                                ),
                                                cls="mt-2",
                                            )
                                        )
                                    elif content_type == "image":
                                        # Render base64 image in tool_result content
                                        source = content_item.get("source", {})
                                        if isinstance(source, dict):
                                            data = source.get("data", "")
                                            media_type = source.get(
                                                "media_type", "image/png"
                                            )
                                            source_type = source.get("type", "base64")

                                            if data and source_type == "base64":
                                                tool_result_components.append(
                                                    Div(
                                                        Img(
                                                            src=f"data:{media_type};base64,{data}",
                                                            alt="Content image",
                                                            cls="max-w-full h-auto rounded",
                                                            style="max-height: 600px;",
                                                        ),
                                                        cls="mt-2",
                                                    )
                                                )

                    # Wrap all tool result components
                    components.append(
                        Div(*tool_result_components, cls="mb-4 p-3 bg-gray-800 rounded")
                    )

                    # Add Tool Result section
                    tool_use_result = event.data.get("toolUseResult")
                    if tool_use_result:
                        components.append(H4("Tool Result", cls="mb-2 font-bold mt-4"))
                        # Handle both dict (native tools) and list (MCP tools) formats
                        if isinstance(tool_use_result, dict):
                            components.append(
                                Div(
                                    *[
                                        Div(
                                            Span(f"{key}: ", cls="text-gray-400"),
                                            Span(
                                                (
                                                    str(value)
                                                    if not isinstance(
                                                        value, (dict, list)
                                                    )
                                                    else ""
                                                ),
                                                cls="text-white",
                                            ),
                                            (
                                                Pre(
                                                    Code(json.dumps(value, indent=2)),
                                                    cls="text-white text-sm whitespace-pre-wrap break-words mt-1",
                                                )
                                                if isinstance(value, (dict, list))
                                                else None
                                            ),
                                            cls="mb-2",
                                        )
                                        for key, value in tool_use_result.items()
                                    ],
                                    cls="mb-4 p-3 bg-gray-800 rounded",
                                )
                            )
                        elif isinstance(tool_use_result, list):
                            # MCP tools return toolUseResult as a list of content items
                            for content_item in tool_use_result:
                                if isinstance(content_item, dict):
                                    item_type = content_item.get("type")

                                    if item_type == "text":
                                        components.append(
                                            Div(
                                                render_markdown_content(
                                                    content_item.get("text", "")
                                                ),
                                                cls="mb-4 p-3 bg-gray-800 rounded",
                                            )
                                        )
                                    elif item_type == "image":
                                        # Render base64 image
                                        source = content_item.get("source", {})
                                        if isinstance(source, dict):
                                            data = source.get("data", "")
                                            media_type = source.get(
                                                "media_type", "image/png"
                                            )
                                            source_type = source.get("type", "base64")

                                            if data and source_type == "base64":
                                                components.append(
                                                    Div(
                                                        Img(
                                                            src=f"data:{media_type};base64,{data}",
                                                            alt="Tool result image",
                                                            cls="max-w-full h-auto rounded",
                                                            style="max-height: 600px;",
                                                        ),
                                                        cls="mb-4 p-3 bg-gray-800 rounded",
                                                    )
                                                )

        elif isinstance(content, str):
            # Simple text content
            components.append(H4("Content", cls="mb-2 font-bold"))
            components.append(
                Div(
                    render_markdown_content(content), cls="mb-4 p-3 bg-gray-800 rounded"
                )
            )

    # Always add Event Data section at the bottom
    formatted_json = json.dumps(event.data, indent=2)
    components.append(H4("Event Data:", cls="mb-2 font-bold mt-4"))
    components.append(
        Pre(
            Code(formatted_json),
            cls="bg-gray-900 text-gray-100 p-4 rounded overflow-auto text-sm",
        )
    )

    return Div(*components)


def Layout(content, show_back_button=False):
    """Main layout wrapper"""
    if show_back_button:
        header = Div(
            A(
                "Back",
                href="/",
                cls="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded",
            ),
            H1("Claude Code Trace Viewer", cls="my-8 text-center flex-grow"),
            Div(style="width: 80px"),  # Spacer to balance the layout
            cls="flex items-center pb-4",
        )
    else:
        header = DivCentered(H1("Claude Code Trace Viewer", cls="my-8"), cls="pb-4")

    return Container(
        header,
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

    # Sort projects by most recent session (descending)
    sorted_projects = sorted(
        projects.items(),
        key=lambda item: max(s.created_at for s in item[1]),
        reverse=True,
    )

    accordion_items = [
        ProjectAccordion(project_name, project_sessions)
        for project_name, project_sessions in sorted_projects
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
    project_name = None
    for session in sessions:
        if session.session_id == session_id:
            session_file = session.file_path
            project_name = session.project_name
            break

    if not session_file or not session_file.exists():
        return Layout(
            Card(
                P(f"Session file not found: {session_id}", cls=TextT.muted), cls="mt-8"
            )
        )

    trace_tree = parse_session_file(session_file)

    # Create tree nodes with previous event context for duration calculation
    tree_nodes = []
    for idx, event in enumerate(trace_tree):
        previous_event = trace_tree[idx - 1] if idx > 0 else None
        tree_nodes.append(TraceTreeNode(event, session_id, trace_tree, previous_event))

    return Layout(
        Div(
            DivFullySpaced(
                H4(f"Session: {session_id}", cls="uk-h4"),
                Span(project_name, cls="text-gray-500 font-normal"),
            ),
            # Combined panel with single border - using CardContainer directly
            CardContainer(
                Div(
                    # Left panel - Trace tree (30% width)
                    Div(
                        Div(
                            *(
                                tree_nodes
                                if tree_nodes
                                else [P("No trace events found", cls=TextT.muted)]
                            ),
                            cls="overflow-auto",
                            style="max-height: 75vh;",
                        ),
                        cls="p-4",
                        style="width: 30%; border-right: 1px solid var(--uk-border-default); height: 75vh;",
                    ),
                    # Right panel - Detail view (70% width)
                    Div(
                        H3("Event Details", cls="mb-4 font-bold"),
                        Div(
                            P("Select an event to view details", cls=TextT.muted),
                            id="detail-panel",
                            cls="overflow-auto",
                            style="max-height: 75vh",
                        ),
                        cls="p-4",
                        style="width: 70%",
                    ),
                    style="display: flex;",
                ),
                cls="mt-4",
            ),
        ),
        show_back_button=True,
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

    # Find previous event for duration calculation
    previous_event = None
    for idx, event in enumerate(trace_tree):
        if event.id == id and idx > 0:
            previous_event = trace_tree[idx - 1]
            break

    return DetailPanel(found_event, trace_tree, previous_event)


# Start server
serve()
