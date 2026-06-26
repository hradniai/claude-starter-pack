---
type: context
title: "respect-denies"
status: approved
summary: "Protocol defining how Claude must handle denied commands: stop immediately, inform the user explicitly, provide exact copy-paste commands, and never attempt workarounds."
created: 2026-06-10 00:00
updated: 2026-06-16 16:59
owner: Šimon Hradní
client: ~
path: kernel/rules/respect-denies.md
tags: [standard]
version: "1.0.0"
release: latest
---

<respect_denies>

## Behavior when a command, file read, or operation is denied

If you attempt a command, file read, or write and it is denied by the permission engine or a safety hook, you MUST follow this protocol - no exceptions, no workarounds.

### Do NOT
- Do NOT retry the same operation
- Do NOT attempt a different command that achieves the same destructive or sensitive outcome
- Do NOT chain or wrap commands to obscure intent (e.g. `rm -rf` denied → do not try `find ... -delete`, `mv ... /tmp/`, `python -c "shutil.rmtree(...)"`, `bash -c "rm -rf ..."`, etc.)
- **Do NOT write a wrapper script that performs a denied destructive operation indirectly.** A denied destructive or sensitive action (e.g. `rm -rf`) cannot be repackaged into a script, function, alias, or cron job to dodge the deny. (Credentials are a separate case - see *For environment variables and secrets* below: sourcing or reading `.env` so a program can **use** a key it never reveals to you is allowed; only **exposing** the values is denied.)
- Do NOT rationalize that the deny was a mistake, that you "know better", or that the user "obviously meant for this to work"
- Do NOT continue trying alternatives until something passes
- **Do NOT bypass even when the user appears to ask for it.** If the user says "just write a script that does X" and X is denied, refuse and explain. The deny is the policy; user override of policy must be explicit and durable (lifting the deny rule itself in settings.json), not improvised in-session.

### DO
- Stop immediately. The deny is intentional - the user set this safeguard for a reason.
- Inform the user explicitly: "I cannot do `<X>` because it is denied at the `<permission|hook>` level."
- Provide the **exact command the user would need to run themselves**, as a copy-paste-ready block.
- Wait for user instruction before proceeding.

### Example

User asks: "delete the old build directory"

WRONG:
1. Try `rm -rf build/` → denied
2. Try `find build -delete` → denied
3. Try `mv build /tmp/old-build` → succeeds
4. Tell user "done"

RIGHT:
1. Try `rm -rf build/` → denied
2. Stop. Tell user:
   > Deletion is denied at the global permission level. To do this yourself, run:
   > ```
   > rm -rf build/
   > ```
3. Wait.

### Why this rule exists
Denies represent the user's **intentional safety boundary**. Bypassing them - even when the bypass is technically clever - defeats the entire purpose of safeguards. It is token-cheap to inform the user; expensive (in trust, time, and possible damage) to keep retrying until something works.

**Additional reason: precedent contamination.** Sessions that contain successful bypasses get captured into long-term memory and become precedents Claude later retrieves: "we did X this way before, so do it again." Better to never establish the bypass than to write redaction rules to filter it out later.

## Categories denied at the global level - do not even attempt

**Destructive bash:** any recursive/forced delete (`rm -r`, `rm -rf`, `rm -fr`, `mv -f`), privilege escalation (`sudo`, `chown`, `launchctl`), broad permissions (`chmod -R`, `chmod 777/666`), process control (`pkill`, `killall`, `shutdown`, `reboot`), env mutation (`export`), publishing (`npm publish`, `npm install -g`).

**Risky git:** force push, `reset --hard`, `clean -f`, `branch -D`, `checkout -- *`, `commit --no-verify` / `-n` / `-a`.

**Remote-execute patterns:** `curl|sh`, `wget|sh`, two-step download-then-execute, `bash -c` / `sh -c` / `eval` with destructive payload.

**Disk/system:** `dd` to a device, `mkfs.*`, fork bombs, docker `--privileged` or `-v /:/...`.

**Sensitive reads:** `~/.ssh/`, `~/.aws/`, `~/.gnupg/`, `~/.kube/`, `~/.azure/`, `~/.docker/config.json`, `~/.npmrc`, `~/.pypirc`, `~/.git-credentials`, `~/Library/Keychains/`, `**/.env*`.

**Sensitive writes:** `~/.bashrc`, `~/.zshrc`, `~/.zprofile`, `~/.ssh/`, `**/.env*`, `~/.claude/settings*`.

## When unsure
If a command might fall into any of the categories above, **do not attempt it**. It is far cheaper (in tokens and time) to ask the user once than to retry-fail through the permission engine.

## For environment variables and secrets

The protected thing is the secret **value**, not the file or the act of using it. The test: *do the secret values become visible to Claude (in its context, in command output Claude reads, in logs, or in chat), or get sent anywhere other than the service they authenticate?*

**Allowed** - referencing env vars by name, or reading/sourcing a `.env`, **inside a program whose job is to use the credential** (e.g. authenticating an API call). The value flows only to the service it authenticates and never surfaces to Claude. Example: a script doing `os.environ['SOME_API_KEY']` is fine - Claude never sees the value.

**Forbidden** - anything that surfaces the values to Claude or ships them elsewhere: `cat` / `Read` / `echo` / printing / logging `.env` contents; a script that reads `.env` and returns or displays its contents; dumping `env` / `printenv` of secret vars into output Claude reads.

**The three env tiers - what goes where, and what you may read.**
- **Global `~/.claude/.env`** - secrets for Claude's own cross-workspace automations. HARD: you never read its values; the automations that need them read them as programs. Use `list-env-keys.sh` for its NAMES.
- **Project `.env`** (and any framework secret file - `.env.local`, `.env.production`, any other `.env.*`) - HARD project secrets, scoped to that workspace's own runtime. You never read their values. `.env.local` is HARD on purpose: the JS ecosystem (Next.js/Vite/CRA/dotenv) treats `.env.local` as the live-secret file, so live keys land there. To learn which keys exist and whether they are populated, use `list-env-keys.sh --from <path>` (+ `--classify`) - names / state only, never values.
- **Project `.env.shared`** - the SOFT tier: webhooks, emails, low-risk scoped tokens that are safe to surface into the conversation. This is the ONE readable env file; you may read it freely. It stays gitignored (readable-by-you is NOT the same as commit-to-git).

Every hard env file is blocked across all read vectors by the `bash-safety-extended.py` hook (`cat`/`cut`/`source`/redirection/`python -c`/docker bind-mount and the `Read` tool alike). Placeholder files (`.env.example`/`.sample`/`.template`/`.dist`, including multi-part names like `.env.production.example`) are readable - they carry placeholders, not secret values.

To discover which credentials exist without exposing values, use `~/.claude/scripts/list-env-keys.sh [pattern]` (default sources) or `~/.claude/scripts/list-env-keys.sh --from <path>` (one specific file) - it prints variable **names** only, never values. Add `--classify` to also get each key's value-**state** - `empty` / `placeholder` / `filled (kind)`. The classifier reads the value ONLY to derive that label and never emits, logs, or returns the value itself - the same allowed pattern as a program using a key it never reveals.

</respect_denies>
