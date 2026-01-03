# Claude Code Trace Viewer

A web viewer for Claude Code session traces from `~/.claude/projects/`.

## Quick Reference

- **Install**: `uv sync`
- **Run**: `uv run python main.py` (opens http://localhost:5002)
- **Lint**: `uvx ruff check main.py`
- **Format**: `uvx black main.py`
- **Type check**: `uvx mypy main.py`

## Project Structure

Single-file application following FastHTML philosophy - all code is in `main.py`:
- Data models: `TraceEvent`, `Session` dataclasses
- Core functions: `discover_sessions()`, `parse_session_file()`
- UI components: `Layout()`, `TraceTreeNode()`, `DetailPanel()`
- Routes: `/`, `/viewer/{session_id}`, `/event/{session_id}/{id}`

## Key Patterns

- **FastHTML routing**: Use `@rt` decorator for routes (see `main.py:672-732`)
- **MonsterUI components**: Container, Card, DivFullySpaced, etc.
- **HTMX updates**: Use `hx_get`, `hx_target` for dynamic content

## Documentation

- `custom-ui-context/fasthtml-conventions.md` - FastHTML patterns
- `custom-ui-context/monsterui-conventions.md` - MonsterUI component reference

## Debugging with Session Logs

When given a session ID (e.g., `a4f450f8-fd66-42ba-b99c-e2c89109d310`), find and read the raw logs:

```bash
find ~/.claude/projects -name "{session_id}.jsonl"
```

Session files contain JSONL with all turns, tool calls, and responses - useful for debugging trace parsing issues.

## Critical Rules

- Use `uv` for package management (never pip directly)
- Keep all application code in `main.py` - only split for massive benefit
- Ruff ignores: F403, F405, F841 (configured in pyproject.toml)
