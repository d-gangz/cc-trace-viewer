# Claude Code Trace Viewer

A web-based viewer for Claude Code session traces, built with FastHTML and MonsterUI.

## Features

- 📁 **Auto-detects your Claude Code sessions** from `~/.claude/projects/`
- 🕐 **Accurate timezone handling** - Automatically converts UTC timestamps to your local time
- 🎯 **Session filtering** - Only shows real conversations, hides summary-only sessions
- 🌲 **Flat timeline view** - Easy-to-read chronological event display
- 🎨 **Interactive UI** - Hover and selection states for better navigation
- ⏱️ **Relative timestamps** - Shows "2 hours ago", "3 days ago", etc.

## Installation

### Prerequisites

- Python 3.11+
- [uv](https://github.com/astral-sh/uv) (recommended) or pip

### Setup

1. Clone this repository:
```bash
git clone https://github.com/d-gangz/cc-trace-viewer.git
cd cc-trace-viewer
```

2. Install dependencies:

**With uv (recommended):**
```bash
uv sync
```

**With pip:**
```bash
pip install -r requirements.txt
```

## Usage

Run the application:

**With uv:**
```bash
uv run python main.py
```

**With python directly:**
```bash
python main.py
```

The application will:
1. Automatically detect your user home directory
2. Scan `~/.claude/projects/` for session files
3. Start a web server at http://localhost:5001

Open your browser and navigate to http://localhost:5001 to view your Claude Code traces.

## How It Works

The viewer:
- Discovers all JSONL session files in your `~/.claude/projects/` directory
- Parses session events and builds a timeline view
- Groups sessions by project
- Shows the most recently active sessions first
- Converts UTC timestamps to your local timezone automatically
- Filters out incomplete sessions (summary-only sessions without actual conversation)

## Project Structure

```
cc-trace-viewer/
├── main.py           # Main application code
├── pyproject.toml    # Project dependencies and metadata
├── uv.lock          # Locked dependencies
└── README.md        # This file
```

## Requirements

- FastHTML - Modern Python web framework
- MonsterUI - UI components for FastHTML
- python-dateutil - Timezone-aware datetime parsing

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

MIT License - feel free to use this for your own projects!

## Troubleshooting

### No sessions showing up?

Make sure:
1. You have Claude Code installed and have created some sessions
2. Your sessions are stored in `~/.claude/projects/`
3. The session files are not empty or summary-only

### Timestamps showing wrong time?

The app automatically converts UTC to your local timezone. If times seem off:
1. Check your system timezone is set correctly
2. Restart the application after changing system timezone

### Port 5001 already in use?

You can change the port in `main.py` by modifying the `serve()` call at the bottom of the file.
