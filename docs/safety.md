# Safety

What the pack protects you against, how, where it stops, and how to check that it is running. Nothing here is secret: the checks are plain Python files in `~/.claude/scripts/`, and this page says what each one recognizes.

## What it is for

The pack is built for Claude Code with Anthropic's Claude models, to protect someone starting out. It aims at four things:

- **Mistakes made in good faith**, by Claude or by you: a recursive delete in the wrong folder, an overwritten file, uncommitted work thrown away, a push straight to `main`.
- **Basic prompt injection**: text planted in a web page, file or tool result that tries to make Claude read secrets, switch off its safety checks or run something downloaded.
- **Basic external risks**, such as a download piped straight into a shell.
- **Leaked API keys** and other secrets read into the conversation.

There are known ways around it. A determined attacker, a model deliberately steered to evade the checks, or a program that opens files itself can get past checks that read command text. Closing every such path is not the goal: each extra rule adds complexity and false alarms that get in a beginner's way. The prompt rules also assume a Claude model that follows its instructions; other models behind Claude Code are outside what the pack was built and tested for. The pack reduces risk; it does not remove it.

## The layers

| Layer | What it does | What it misses |
|---|---|---|
| 1. Permission rules in `~/.claude/settings.json` | Lets routine work run, asks you before risky actions, refuses destructive ones, keeps bypass permissions mode locked | The same action written another way; programs that open files themselves |
| 2. Two hooks (small programs Claude Code runs before each command, file read and search) | Read the whole command and block the actions listed below, also in forms the rules miss | Anything not on their lists; a program Claude writes and runs later; data sent out over an allowed channel |
| 3. Two prompt rules, `respect-denies` and `untrusted-content` | Tell Claude to stop at a block instead of finding a way around it, and to treat what it reads as information, never as orders | Nothing is enforced: they lower the risk of prompt injection, they do not remove it |

What you add yourself sits outside all three: a folder you trust, a plugin, an MCP server (a connection to an outside service) or a skill you install runs with your access ([getting-started.md, "Trust and your data"](getting-started.md#trust-and-your-data)).

Claude Code adds two layers of its own, which the pack neither installs nor changes. **Auto mode** is its starting mode in the terminal and VS Code where your plan and model support it: a second AI model reviews the actions no permission rule settles and blocks risky ones. Hooks still run in Auto mode, and an ask rule still prompts you. On entering Auto mode, Claude Code drops broad allow rules that would let any code run (such as `Bash(python3 *)`) and sends those calls to the reviewer instead. Anthropic is plain about it: "Auto mode reduces permission prompts but does not guarantee safety" ([permission modes](https://code.claude.com/docs/en/permission-modes)). **The sandbox** is optional, see [Stronger options](#stronger-options).

## Layer 1: permission rules

- **Run without asking:** reading, searching and editing files, git, build and test tools, running Python and Node, web fetches and searches, media tools.
- **Ask you first:** package installs (npm, pip including `python -m pip install`, Homebrew, `go install` and `go get`, `go run` of a downloaded package, `cargo install`), `npx`, `docker run` and `docker pull`, `git push`, `merge` and `rebase`, network transfers (`curl`, `wget`, `ssh`, `scp`, `rsync`), deletes (`rm`, a narrowed `find -delete`), `kill`, and Claude editing its own settings or scripts.
- **Refused:** destructive commands (recursive `rm`, `sudo`, `chmod -R`, `chown`, `dd`, `mkfs`, force pushes, `git reset --hard`, `git clean -f`, `git branch -D`, skipping git hooks, `npm publish`, `shutdown` and more), edits to your shell startup files and `~/.ssh`, reads of credential files (SSH, cloud, registry and database credentials, password stores, browser profiles, Claude Code's own login file, also in the installer's backup `~/.claude.bak-*`), and reads of secret env files.
- **Bypass permissions mode is locked** (`disableBypassPermissionsMode`). That mode runs almost everything without a prompt or review, and Anthropic warns that it "offers no protection against prompt injection or unintended actions". Removing the lock is an edit to `settings.json`, which asks you first.

Claude Code matches these rules against the command text. By [its own documentation](https://code.claude.com/docs/en/permissions) they do not stop the same program written another way or a program that opens files itself; that is what the hooks are for. The full lists are in `~/.claude/settings.json`.

## Layer 2: the hooks

### The safety hook, `bash-safety-extended.py`

It runs before every command Claude runs through its Bash tool (the shell), every use of its Read and Grep tools (reading and searching files), and every command of Claude Code's Monitor tool (which runs commands in the background and exists only when telemetry is on). It reads a command the way the shell would: it follows `cd` and variables, looks inside `bash -c`, `eval`, `xargs`, `find -exec`, pipes and subshells, and understands Windows path forms (`C:\...`, `/c/...`). It blocks:

- **Forced recursive deletes**: `rm -rf` in its common spellings and positions (`-r -f`, `--recursive --force`, flags after the path, behind `sudo`, `env` or `/bin/rm`), inline code that does the same (`shutil.rmtree`, a recursive `rmSync`), the Windows forms (`rd /s`, `del /s`, `Remove-Item -Recurse`), and `find -delete` over a whole folder tree. A narrowed delete such as `find . -name '*.pyc' -delete`, and plain `rm`, ask you instead.
- **Overwriting moves and copies**: an `mv`, or a `cp` of a file, onto an existing file (a symbolic link to a file counts, since the copy writes into its target), or into a folder that already holds that name. `-n`, `-i` and `--backup` pass, for `mv` and `cp` alike, and so does `cp -u` when the destination is not older than the source, because `cp -u` then leaves it alone. Copying a whole folder (`cp -R folder dest`) is not checked: it merges into an existing folder, as builds and installs do all the time.
- **Searches over the whole disk or the home folder**: a recursive search (`grep -r`, `rg`, `ag`, `ack`, and Claude's Grep tool) that starts at `/`, a whole drive (`C:\`, `/c`), your home folder itself or a folder above it (`/Users`, `/home`), whatever it prints (`-l` and `-c` read every file too). Such a search reads every file below it and can run for minutes and use up the computer's memory until it stops responding. Searching the project folder or a folder inside your home folder (`~/Documents/...`) passes, and so does listing file names (`find`, `rg --files`).
- **Throwing away uncommitted work**: `git restore` of files (without `--staged`), `git checkout -f`, `git checkout .` and other checkouts of files or folders, `git switch --discard-changes` or `-f`, `git stash drop` and `git stash clear`. Unstaging, `git stash` and changing branches pass.
- **Raw disk writes and risky containers**: `dd`, `mkfs`, `fdisk`, `diskutil erase`, writes onto disk devices, `diskpart` and `format` on Windows, fork bombs, `docker run --privileged`, and docker mounts of `/`, of system folders, of folders holding credentials or of the Docker socket.
- **Credential reads**: any command that reads, copies, archives or uploads a listed credential location: `~/.ssh` (the hook lets public keys `*.pub` through, but the permission rules still keep Claude out of the whole folder, so to share your public key, open the `.pub` file yourself), `~/.gnupg`, `~/.aws`, `~/.azure`, `~/.kube`, gcloud, `~/.docker/config.json`, `~/.config/gh`, `~/.git-credentials`, `~/.netrc`, `~/.npmrc`, `~/.pypirc`, package-registry and database tokens, password stores, keychains, browser profiles, Claude Code's own login file (also in copies of `~/.claude` such as the installer's backup), and their Windows equivalents. Key and folder names are recognized anywhere on disk, so a copy elsewhere is still protected. Tools that use a key without printing it (`ssh`, `ssh-add`, `scp -i`, `gpg` key management) and commands that only list names (`ls`, `stat`) keep working.
- **Env-file reads**: reading the values of a secret env file (see the tiers below) in any way, such as `cat`, `grep`, `sed`, `source`, `< .env`, inline code, copying it to a name outside the env files, archiving or uploading it, or a recursive search over its folder. An archive of a folder that holds one directly (`tar -czf b.tgz .`, `zip -r b.zip .`, `7z a`) is blocked too, unless the command excludes it at every depth: `tar --exclude='.env*'`, `zip ... -x '*.env*'` or `7z ... '-xr!.env*'`. A pattern with a folder in it, or zip's `-x .env` (which matches only a file stored at the top of the archive), does not count, and an exclude that names the file exactly (`--exclude=.env`) is refused as a read of it: use the wildcard forms above.
- **Grep searches that would print secrets**: Claude Code's Grep tool also searches hidden files, so a search aimed at a credential location or a secret env file is blocked, and so is a content search over a folder that holds credential folders (such as your home folder) or holds a credential file directly (such as `~/.claude` and its backups, where Claude Code may keep its login). A content search whose glob ends in a bare wildcard, such as `src/**`, is blocked too, because a glob makes Grep read files that `.gitignore` hides: set the search path to that folder instead.
- **Changes to the safety layer itself**: any shell command that writes `~/.claude/settings.json`, `settings.local.json` or `~/.claude/scripts/`, through a redirect, `cp`, `mv`, `tee`, `sed -i`, a download, or by unpacking an archive or applying a patch into `~/.claude` or a folder above it (the file names inside an archive do not show on the command line). Unpacking into `~/.claude/rules`, `skills`, `agents`, `workflows` or `templates`, and copying from `~/.claude` to somewhere else, such as a backup, pass. Claude's file-editing tool can still change these files, and asks you first. Claude Code applies an edited settings file at once, so a single such command could otherwise switch every check off; it is also why the installer has you run some copies yourself when you update the pack.
- **Download-and-run**: a download piped or fed straight into a shell (`curl ... | sh`, `bash <(curl ...)`, `eval "$(curl ...)"`, PowerShell's `irm ... | iex`), decoded content piped into a shell (`base64 -d | sh`), and a file downloaded and run in the same command. Downloading to a file passes.
- **Skipped git hooks**: `git commit --no-verify` or `-n`, and pointing git at another hooks folder (`core.hooksPath`), so a check you add before each commit runs on every commit Claude makes.
- **Deny-list commands in disguise**: inside `bash -c`, `eval`, `xargs`, `find -exec` or `wsl`, or behind an absolute path, quotes or `.exe`, the hook applies the refused list of `settings.json` itself. Plain forms stay with `settings.json`, so loosening a rule there is not silently overridden.
- **The PowerShell tool**: every call, because the hook reads bash only. The pack also keeps that tool off (`CLAUDE_CODE_USE_POWERSHELL_TOOL=0`). PowerShell code started from the Bash tool (`powershell -NoProfile -Command '...'`) is checked.

A blocked call gets a message that starts `BLOCKED by bash-safety-extended`, says why, and tells Claude not to try another way. The hooks never ask: a call passes or is blocked.

### The push guard, `git-push-guard.py`

It stops a `git push` that would update `main` or `master` on the remote: `git push origin main`, `HEAD:main`, `--all`, `--mirror`, a bare `git push` while `main` is checked out, and similar forms. Branch names that only contain the word (`feature/main-menu`), tags and `--dry-run` pass. It enforces a habit, changes going through a branch you can review, rather than a safety boundary: a merge on GitHub is not a push. It reads Bash calls only, not the Monitor tool. If you push straight to `main` on purpose, remove its entry from `settings.json`.

### Env files: three tiers

- **Secret, never read:** `~/.claude/.env` and every project `.env`, `.env.local`, `.env.*` and `.envrc`. Your programs use them; Claude never sees the values.
- **Readable:** `.env.shared`, for values that grant nothing (a contact address, a public URL, a feature flag), and templates (`.env.example`, `.env.sample`, `.env.template`, `.env.dist`). A webhook URL is a secret, because whoever holds it can post or trigger through it: it goes in `.env` or `~/.claude/.env` with the keys.
- **Names only:** `~/.claude/scripts/list-env-keys.sh` shows which keys exist, never their values; `--classify --from <file>` adds, for that one file (`./.env` without `--from`), whether each key is empty, a placeholder or filled.

Commands that only point at an env file pass: `--env-file .env`, `cp .env .env.bak`, appending a line, `ls`. The permission rules cover env files in the folder Claude works in; the hook covers them anywhere on disk.

## Layer 3: the prompt rules

- **`respect-denies`**: at a block, Claude stops that operation, never retries it or reaches the same result another way, and says what was blocked. It hands you the exact command to run yourself only for a goal you asked for; for an operation that came from something it read, it explains the block and does not pass the command on.
- **`untrusted-content`**: apart from your request and the instructions you set up, everything Claude reads is information, not orders, including a `CLAUDE.md` in a repository you cloned. Content never changes the task, grants approval, weakens a safeguard or gets written into rules, settings or instruction files, and private data goes only where you sent it (search queries and URLs count). Each clear attempt is reported as one line starting `SUSPECTED PROMPT INJECTION`. The research skill, agents and workflow repeat these points, because research reads the most outside material.

## What it does not protect against

- **Programs that open files themselves.** A script Claude writes and then runs, or a file downloaded in one call and run in the next, is invisible to a check of command text. Only the sandbox covers this.
- **Inline code beyond simple patterns.** Python, Node or PowerShell code is scanned for a few well-known calls and paths; code that builds a path or a command from pieces passes.
- **Forms the hook does not model**: some archive tools, options that make a tool run another program, git aliases, values built up across several commands, and settings files of other tools (such as `~/.wgetrc` or git's configuration) that change what a later command does.
- **Secrets a program already holds**, such as a key exported into your shell or a tool that prints its own stored credentials on request, and **credential files not on the list**.
- **Tools the hooks do not inspect**: MCP tools, `WebFetch`, `WebSearch` and `Glob`. File edits through Claude's editing tool are covered by the permission rules only.
- **Secrets deeper in a folder**: a recursive search or an archive is checked for secrets in its top folder only, so an archive of a whole project takes a nested `.env` (such as `backend/.env`) along. A recursive copy on this disk (`cp -R`, `rsync`) is not checked for secrets at all.
- **Overwrites the hook does not model**: copying a whole folder (`cp -R`) over an existing one replaces same-named files inside it without a check, and so do `rsync`, `install`, unpacking an archive and a redirect (`>`); only `mv` and a `cp` of single files are checked.
- **What runs elsewhere**: commands run over `ssh` on another machine or inside a container.
- **Data sent out over an allowed channel.** Claude reads files and fetches web pages without asking, so text planted in a page could steer it to send private data out. `curl`, `wget` and `ssh` ask you first, but a fetched URL (`WebFetch`), a search query, an MCP tool, a feature branch pushed once you approve the push, or a program Claude runs can still carry data out. The `untrusted-content` rule tells Claude not to; nothing enforces it.
- **A determined attacker on your machine**, and **plain mistakes in Claude's work**, such as wrong but runnable code. Review what matters.

## When the hooks are off, or block everything

In these setups the hooks do not run, and nothing tells you; the permission rules still apply:

- **Windows without Git for Windows.** Claude Code then runs hooks through PowerShell, where they cannot start, and a hook that cannot start does not block ([hooks](https://code.claude.com/docs/en/hooks)). The installer requires Git for Windows for this reason.
- **The Desktop app's Code tab on some versions.** The documentation says hooks from settings apply there, but four open GitHub issues from August and September 2026 report hooks not loading, or some events never firing, in the Code tab on macOS and Windows: [#87657](https://github.com/anthropics/claude-code/issues/87657), [#95833](https://github.com/anthropics/claude-code/issues/95833), [#96496](https://github.com/anthropics/claude-code/issues/96496), [#97977](https://github.com/anthropics/claude-code/issues/97977). The installer tests this live in the app. If the test command runs there, do risky work in the terminal until a fixed version arrives.
- **Settings managed by an organization**, on a company computer, can switch off the pack's hooks or its permission rules. The installer checks for them and tells you.
- **Changed defaults.** Turning telemetry back on (removing `DISABLE_TELEMETRY`) also brings back the Monitor tool, which runs commands in the background: the safety hook checks them, the push guard does not, and the ask rule on `git push` still prompts. Turning the PowerShell tool on means removing `PowerShell` from the safety hook's matcher, and its commands then run unchecked.

The opposite failure is deliberate. With **no usable Python 3.9 or newer**, or a hook that fails to load or crashes, every Bash, Read and Grep call is blocked with a message saying what to install or that the safety layer needs repair, because a check that cannot run must not wave commands through. A command the hook cannot analyse (nested too deeply, too long) is blocked too, with a request to split it into simpler steps. Scripts whose line endings an editor or sync tool changed to the Windows form would also block everything: copy them again from a fresh clone, whose `.gitattributes` keeps them right.

## Check that the hooks run

A refusal alone proves little: the permission rules refuse `rm -rf` or a `.env` read even where no hook runs. Step 2.1 of [INSTRUCTIONS.md](../INSTRUCTIONS.md#21-confirm-the-safety-layer-is-live) has two harmless test commands that only the hook stops, and how to read the result. The installer runs them in the app you install from; ask Claude to run them again in every other app where you use Claude Code. In a terminal, `/hooks` lists the hooks Claude Code loaded.

## Stronger options

- **The sandbox.** `/sandbox` turns on Claude Code's operating-system sandbox (macOS, Linux and WSL2, not native Windows). It limits which files and network addresses Bash commands, and the programs they start, can reach, so it also covers programs that open files themselves. It does not cover `WebFetch` or MCP tools ([sandboxing](https://code.claude.com/docs/en/sandboxing)).
- **Manual mode.** Set `"defaultMode": "default"` under `permissions` in `~/.claude/settings.json`. With this pack, Manual is not automatically stricter: Auto mode sends broad allow rules such as `Bash(python3 *)` to its reviewer, while Manual runs them without one. Move the allow rules you want checked to `ask` when you switch.
- **Web access behind a prompt.** Remove the `WebFetch` allow rule and add `"WebFetch"` to `ask`, or allow only `WebFetch(domain:...)` rules for sites you trust. In Auto mode, removing the allow rule alone sends fetches to the reviewer instead of asking you. A search query can carry private text too, so consider `WebSearch` the same way.
