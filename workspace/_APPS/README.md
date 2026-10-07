---
type: core
title: "_APPS"
status: active
summary: "Small apps and tools you build: the per-app layout, what belongs here versus elsewhere, and the bundled example."
created: 2026-05-01
updated: 2026-10-05
created_by: claude-starter-pack
client: ~
path: _APPS/README.md
tags: [readme]
version: "1.0.0"
---

# _APPS

Small apps and tools you build. Each app is a self-contained subdirectory, best scaffolded by starting Claude in a new folder here and running `/setup` (type "App"). Run Claude from the app's folder, not from `_APPS/` itself.

```
_APPS/
└── my-tool/
    ├── CLAUDE.md         what the tool does, status, tech stack
    ├── README.md         for users: install, usage, examples
    ├── src/              source code (or scripts/)
    ├── tests/            if any
    └── examples/         sample inputs
```

## What goes where

- **`_APPS/`** - reusable tools you run more than once: CLI scripts, small web apps, MCP servers, converters.
- **`_BUSINESS/scripts/`** - one-off utilities for your own workflow, not packaged or shared.
- **`_CLIENTS/<client>/projects/<project>/`** - code that is part of a client deliverable.
- **`~/.claude/scripts/`** - utilities Claude itself uses across projects (like `list-env-keys.sh`).

## Bundled example: `_example-app-transcribe/`

A stub that shows the layout for a transcription tool calling an LLM API. It does nothing until you implement the API call; its README says what to build. Delete the folder if you do not want it.
