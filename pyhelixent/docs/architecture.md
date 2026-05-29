# Architecture

PyHelixent is intentionally small. It preserves the agent control flow while avoiding provider SDKs, terminal UI code, and production permission systems.

## Data Flow

```text
UserMessage
   |
   v
Agent.stream()
   |
   +-- before_agent_run hooks
   |
   +-- step N
       |
       +-- before_agent_step hooks
       +-- before_model hooks
       +-- Model.stream(ModelContext)
       +-- after_model hooks
       +-- AssistantMessage appended
       |
       +-- tool_use content?
           |
           +-- before_tool_use hooks
           +-- Tool.invoke(input)
           +-- after_tool_use hooks
           +-- ToolMessage appended
       |
       +-- after_agent_step hooks
```

The transcript is the source of truth. The model sees the current prompt, messages, and tools through `ModelContext`.

## ReAct Loop

ReAct is represented as repeated model/tool turns:

- Reason: the model emits text and optionally one or more tool calls.
- Act: the agent finds each tool by name and invokes it with the supplied input.
- Observe: the agent appends `ToolMessage` observations back into the transcript.

When the model emits no tool calls, the agent run is complete.

## Middleware

Middleware is a list of hook objects. Hooks run in list order. A hook can:

- observe state
- return a dictionary of context updates
- skip a tool call with `SkipToolUse`

This keeps extension behavior outside the agent loop while making each lifecycle point visible.

## Skills

Skills use the common folder convention:

```text
<skills_dir>/<skill_name>/SKILL.md
```

Only front matter is loaded during discovery:

```markdown
---
name: coding-plan
description: Helps plan coding tasks.
---
```

The skills middleware injects discovered skills into the prompt as lightweight XML-like tags. A real model can then decide to read and follow a skill file.

## Tool Safety

Coding tools receive a workspace root and resolve file paths through it. Paths outside the workspace are rejected. The shell tool runs in the workspace with a timeout and blocks a small set of destructive commands by default.

