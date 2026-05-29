# PyHelixent

PyHelixent is a small Python learning project that recreates the core ideas of the JavaScript Helixent agent in a compact, readable form.

The goal is not feature parity. The goal is to make the basic mechanics of an agent visible:

- a ReAct-style `think -> act -> observe` loop
- model, message, and tool primitives
- lifecycle hooks through middleware
- skill discovery and prompt injection
- a few coding-oriented tools
- tests that explain the behavior

## Project Layout

```text
pyhelixent/
├── AGENTS.md              # Development guide for future agents
├── README.md              # This overview
├── pyproject.toml         # Packaging and test configuration
├── docs/
│   └── architecture.md    # Design notes and data flow
├── src/pyhelixent/
│   ├── foundation/        # Message, model, and tool primitives
│   ├── agent/             # ReAct loop and middleware hooks
│   ├── skills/            # SKILL.md discovery and prompt middleware
│   ├── coding/            # Learning-oriented file/search/shell tools
│   └── cli.py             # Tiny demo CLI
└── tests/                 # Unit and integration-style tests
```

## Quick Start

Run from the repository root:

```bash
cd pyhelixent
python -m venv .venv
source .venv/bin/activate
python -m pip install -e .
python -m pyhelixent "list files"
```

The project intentionally uses only the Python standard library, so the editable install is only for import convenience.

## Run Tests

```bash
cd pyhelixent
python -m unittest discover -s tests
```

## Core Concepts

### Foundation

The `foundation` package contains stable primitives:

- `Message` dataclasses for user, assistant, and tool messages.
- `Model` protocol and `ModelContext`, so agent code does not know about a provider.
- `Tool` and `define_tool`, so actions are described and invoked consistently.

### Agent Loop

`Agent.stream()` keeps a transcript and repeats:

1. append a user message
2. call middleware hooks
3. ask the model for an assistant message
4. emit any assistant output
5. execute tool calls, possibly in parallel
6. append tool results
7. continue until the model stops requesting tools

### Middleware Hooks

Middleware can observe or modify the run through hooks such as:

- `before_agent_run` / `after_agent_run`
- `before_agent_step` / `after_agent_step`
- `before_model` / `after_model`
- `before_tool_use` / `after_tool_use`

`before_tool_use` can return `SkipToolUse(result=...)` to bypass a tool call.

### Skills

Skills follow a simple `SKILL.md` folder convention. The skills middleware discovers skills, reads front matter, and injects skill information into the model prompt before each run.

```text
skills/
└── coding-plan/
    └── SKILL.md
```

## Demo Behavior

The built-in demo uses a deterministic learning model rather than a real LLM. That keeps tests and examples reliable while still showing the same control flow a real model would use.

For real provider integration, add a new class that implements the `Model` protocol and returns `AssistantMessage` snapshots from `stream()`.
