<respect_denies>

## Behavior when a command, file read, or operation is denied

If you attempt a command, file read, or write and it is denied by the permission engine or a safety hook, you MUST follow this protocol - no exceptions, no workarounds.

### Do NOT
- Do NOT retry the same operation
- Do NOT attempt a different command that achieves the same destructive or sensitive outcome
- Do NOT chain or wrap commands to obscure intent (e.g. `rm -rf` denied → do not try `find ... -delete`, `mv ... /tmp/`, `python -c "shutil.rmtree(...)"`, `bash -c "rm -rf ..."`, etc.)
- Do NOT rationalize that the deny was a mistake, that you "know better", or that the user "obviously meant for this to work"
- Do NOT continue trying alternatives until something passes

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

## Categories denied at the global level - do not even attempt

**Destructive bash:** any recursive/forced delete (`rm -r`, `rm -rf`, `rm -fr`, `mv -f`), privilege escalation (`sudo`, `chown`, `launchctl`), broad permissions (`chmod -R`, `chmod 777/666`), process control (`pkill`, `killall`, `shutdown`, `reboot`), env mutation (`export`), publishing (`npm publish`, `npm install -g`).

**Risky git:** force push, `reset --hard`, `clean -f`, `branch -D`, `checkout -- *`, `commit --no-verify` / `-n` / `-a`.

**Remote-execute patterns:** `curl|sh`, `wget|sh`, two-step download-then-execute, `bash -c` / `sh -c` / `eval` with destructive payload.

**Disk/system:** `dd` to a device, `mkfs.*`, fork bombs, docker `--privileged` or `-v /:/...`.

**Sensitive reads:** `~/.ssh/`, `~/.aws/`, `~/.gnupg/`, `~/.kube/`, `~/.azure/`, `~/.docker/config.json`, `~/.npmrc`, `~/.pypirc`, `~/.git-credentials`, `~/Library/Keychains/`, `**/.env*`.

**Sensitive writes:** `~/.bashrc`, `~/.zshrc`, `~/.zprofile`, `~/.ssh/`, `**/.env*`, `~/.claude/settings*`.

## When unsure
If a command might fall into any of the categories above, **do not attempt it**. It is far cheaper (in tokens and time) to ask the user once than to retry-fail through the permission engine.

## For environment variables
`.env` files hold secret VALUES that must never enter Claude's context. They are denied for a reason, and a `bash-safety-extended.py` hook enforces it across every read vector (`cat`/`cut`/`source`/redirection/`python -c`/docker bind-mount, and the `Read` tool).

**The single deliberate exception - `.env.local`.** Every other `.env` / `.env.*` file is hard-blocked for reading. The ONE file whose real values you may read is **`.env.local`** - the deliberate, single channel for handing Claude an API key or token. The user creates it in a project on purpose, only when Claude genuinely needs a credential. Reading it is allowed and expected; you never write or commit it (it stays gitignored via the `.env.*` pattern). Non-secret templates (`.env.example`/`.sample`/`.template`/`.dist`) are also readable.

To work with credentials in any other `.env` file without exposing values:
1. Run `~/.claude/scripts/list-env-keys.sh --from <path>` (one file) or `list-env-keys.sh [pattern]` (default sources) to discover variable **names** only, never values.
2. Reference the variable by name in code: `os.environ['GEMINI_API_KEY']`.
3. The value reaches only the service it authenticates; it never surfaces to Claude.

</respect_denies>
