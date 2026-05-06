# _APPS

Small apps and tools you build. Each app is a self-contained subdirectory.

## Convention

```
_APPS/
└── my-tool/
    ├── AGENTS.md         ← what the tool does, status, tech stack
    ├── CLAUDE.md         ← symlink to AGENTS.md
    ├── README.md         ← user-facing readme (install, usage, examples)
    ├── notes.md          ← brain dump for development
    ├── src/              ← source code (or scripts/, depending on language)
    ├── tests/            ← if any
    └── examples/         ← input examples for testing
```

## When to put something here vs. somewhere else

- **`_APPS/`** — reusable tools you'll run more than once. CLI scripts, mini web apps, MCP servers, file converters.
- **`_BUSINESS/scripts/`** — small one-off utilities for your own workflow. Not packaged, not shared.
- **`_CLIENTS/{client}/projects/{project}/`** — code that's part of a client deliverable.
- **`~/.claude/scripts/`** — system-level utilities used across projects (like `list-env-keys.sh`).

## Bundled example: `_example-app-transcribe/`

A minimal stub showing the structure for a transcription tool that uses an LLM API. **It's a stub — you'll need to implement the actual API call before it does anything useful.** Read its README for what to build out.

If you don't want it, delete the directory:
```bash
rm -rf _APPS/_example-app-transcribe
```
