# PyHelixent Agent Guide

This file is project memory for future coding agents working in `pyhelixent`.

## Purpose

Build a compact, educational Python agent that mirrors the important ideas of Helixent without copying all production features.

Keep the code easy to read. Prefer explicit data flow over clever abstractions.

## Architecture

Use these layers and keep dependency direction simple:

- `foundation`: pure primitives only. No agent-specific or coding-specific imports.
- `agent`: generic ReAct loop and middleware. Depends on `foundation`.
- `skills`: skill discovery and middleware. Depends on `foundation` and `agent`.
- `coding`: practical tools for filesystem/search/shell demos. Depends on `foundation`.
- `cli`: thin entry point that wires the pieces together.

## Conventions

- Python version: 3.11+.
- Use only the standard library unless a new dependency clearly improves learning value.
- Public object names use clear nouns: `Agent`, `Tool`, `ModelContext`, `AssistantMessage`.
- Keep files small and focused.
- Prefer dataclasses for message/content/tool data.
- Tool names exposed to the model use `snake_case`.
- Hook names mirror lifecycle timing: `before_model`, `after_tool_use`, etc.
- Tool implementations should return plain values or structured dictionaries; the agent loop serializes observations.
- File tools must stay inside their configured workspace root.
- Shell tools should use a timeout and conservative defaults.

## Testing

Use `unittest` from the standard library.

Test behavior at the layer that owns it:

- `foundation`: tool definition and scripted model behavior.
- `agent`: step loop, tool result appending, middleware ordering, skipped tools.
- `skills`: front matter parsing, discovery, prompt injection.
- `coding`: path safety and tool outputs.

Run:

```bash
python -m unittest discover -s tests
```

## Git Workflow

New feature work should start from `main` on a feature branch.

Suggested commit slices:

1. documentation and project skeleton
2. foundation and agent loop
3. skills and coding tools
4. tests and polish

Do not rewrite unrelated user changes.
