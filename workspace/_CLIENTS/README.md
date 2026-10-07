---
type: core
title: "_CLIENTS"
status: active
summary: "One subdirectory per client engagement: where to run Claude, and how to add a client."
created: 2026-05-01
updated: 2026-10-05
created_by: claude-starter-pack
client: ~
path: _CLIENTS/README.md
tags: [readme]
version: "1.0.0"
---

# _CLIENTS

One subdirectory per client engagement.

## Run Claude from a client folder, not from here

Start Claude in a specific client folder (e.g. `~/Documents/_CLIENTS/acme-corp/`), never in `_CLIENTS/` itself. Each client has its own `CLAUDE.md`, knowledge base and projects; context is per client and must not mix. Started here, Claude has no client context and produces generic work.

## Adding a client

Start Claude in a new, empty folder here and run `/setup` (type "Client"): it writes `CLAUDE.md`, the folder structure, ignore and env templates, and a local git history.

Or copy `_example-client/` to a folder named for the client and fill in its `CLAUDE.md`.

`_example-client/CLAUDE.md` shows the structure and the constraints for client work.
