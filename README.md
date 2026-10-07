# Claude Code Starter Pack

A ready-made setup for [Claude Code](https://code.claude.com/docs/en/setup), Anthropic's AI agent that works directly on your computer: it reads and edits your files and runs commands to finish a task. That power is also the risk. This pack sets Claude Code up so that the worst accidents are blocked, every session leaves notes the next one can pick up from, research says where each claim comes from, and your work has a tidy place to live.

It is for people starting out with Claude Code who want a safe, organized setup from day one. The defaults are a starting point: you will add rules, build skills and loosen or tighten permissions as you learn what you trust. New to Claude Code itself? [docs/getting-started.md](docs/getting-started.md) explains the basics in plain words, and at the end of the install Claude offers to walk you through it.

## Where it works

Claude Code in a terminal (the text window where you type commands) and in the Code tab of the Claude Desktop app, on macOS, Windows and Linux. The VS Code and JetBrains extensions read the same settings, so the pack applies there too. It does not install into other tools such as Claude Cowork, Codex or Cursor, though Claude can help you carry parts over by hand. One caveat: open bug reports describe Claude Code's hooks (the small programs that run the pack's safety checks) not running in the Desktop app's Code tab on some versions ([details](docs/safety.md#when-the-hooks-are-off-or-block-everything)). The installer tests this live and tells you the result; a terminal is the reliable place to install from.

## Before you start

Not sure about any of this? Skip the list: Claude checks all of it first and tells you exactly what to install.

- **Claude Code**, installed, signed in, and updated right before you install: `claude update` in a terminal (installed with Homebrew: `brew upgrade claude-code`; with WinGet: `winget upgrade Anthropic.ClaudeCode`; the Desktop app updates itself when you quit and reopen it). It needs a paid Claude plan (Pro, Max, Team or Enterprise) or an Anthropic Console account. [Install guide](https://code.claude.com/docs/en/setup); never used a terminal? Anthropic's [terminal guide](https://code.claude.com/docs/en/terminal-guide) shows how to open one.
- **Git**, the tool that keeps a version history of your files. On Windows it is required even if you never use it yourself: Git for Windows includes Git Bash, without which the pack's safety checks cannot run at all.
- **Python 3.9 or newer**, because the safety checks are small Python programs. On macOS, `xcode-select --install` provides both Python and Git. On Linux, use your package manager; Ubuntu 20.04 and Debian 10 ship a Python that is too old.

<details>
<summary><b>Windows: one-time preparation</b></summary>

1. **Git for Windows:** download it from [git-scm.com/downloads/win](https://git-scm.com/downloads/win), run it and click Next on every screen; the default options are right.
2. **Python:** download it from [python.org/downloads](https://www.python.org/downloads/). With the classic installer, tick "Add python.exe to PATH" on its first screen. With the Python install manager, run `py install default` in a new PowerShell window afterwards.
3. **Open PowerShell**, Windows' built-in terminal: press Win+X and choose Windows PowerShell or Terminal. Open a new window after steps 1 and 2, so it finds the new programs.
4. **Claude Code in the terminal**, if you have used it only in the Desktop app: paste `irm https://claude.ai/install.ps1 | iex` into PowerShell and press Enter. This is Anthropic's official installer; the pack later stops Claude from running downloads this way, but you typing Anthropic's own command is fine. Open a new window, type `claude`, sign in, then type `/exit`.

</details>

## Install

It takes about 15 to 30 minutes by our estimate, longer if Git or Python must be installed first (Claude then asks you to restart Claude Code once more before it starts), with one restart of Claude Code halfway.

1. **Get the pack.** Open a terminal (macOS: Cmd+Space, type Terminal, press Enter; Windows: PowerShell, see above) and run:

   ```bash
   git clone https://github.com/hradniai/claude-starter-pack.git
   cd claude-starter-pack
   claude
   ```

   No Git? On the pack's GitHub page click **Code**, then **Download ZIP**, and unzip it; in a terminal type `cd` and a space, drag the folder into the window, press Enter and type `claude`. From the Desktop app instead: in the Code tab choose **Local** and select the pack folder as the project folder.
2. **Trust the folder.** Claude Code asks whether you trust the files in this folder. Say yes: it is the pack you just downloaded, and every file in it is plain text you can read first. For other folders, say yes only when you know where they come from ([why](docs/getting-started.md#trust-and-your-data)).
3. **Ask Claude to install it.** Type:

   > Read INSTRUCTIONS.md and guide me through installing this pack.

   Claude checks your computer, shows you one plan, and installs after your yes. Claude Code may also show its own permission box before a command runs ("Do you want to proceed?"): read what the command does, then answer; Esc means no ([more](docs/getting-started.md#your-first-five-minutes)).
4. **Restart once, when Claude asks.** The new session runs on the installed files alone, so Claude can prove there that the safety checks really run. Terminal: type `/exit`, then `claude`. Desktop app: quit it completely (macOS: Cmd+Q; Windows: also quit it in the system tray next to the clock) and open it again. Then type:

   > Read INSTRUCTIONS.md and continue the installation from INSTALL-PROGRESS.md.

Keep the pack folder afterwards: the documentation lives there, and it is how you update ([docs/customization.md](docs/customization.md#updating-the-pack)).

## What changes on your computer

- **`~/.claude/`**, Claude Code's settings folder in your home folder (on Windows `C:\Users\<you>\.claude`). It is first copied to a backup, `~/.claude.bak-<date>-<time>`, then receives the parts below. A configuration you already have is merged with your consent, never overwritten blindly.
- **Your work folder**, `~/Documents/` by default, gets four new folders. A folder that already exists is never overwritten. If Documents syncs to OneDrive or iCloud, Claude asks whether your client files should be uploaded there or live in a local folder instead.
- **Settings that differ from Claude Code's defaults**, listed in the plan and kept unless you ask to change one:

| Setting | Pack | Claude Code's default | Trade-off |
|---|---|---|---|
| Keeping session transcripts (`cleanupPeriodDays`) | 3650 days | 30 days | `/resume` (reopen an earlier conversation) can return to old sessions for years; transcripts are plain text holding everything Claude read, so if you handle other people's personal data, a shorter period may suit you better |
| Usage telemetry and error reports to Anthropic | off | on | They stay on your computer (your conversation still goes to Anthropic to be answered). Side effect: features Anthropic switches on remotely stay off, and so does the Monitor tool, which runs commands in the background |
| Agent teams, an experimental multi-agent feature | available | unavailable | Nothing starts unless you ask for a team |
| Feedback surveys | off | shown | Fewer interruptions |
| PowerShell tool, Claude's way of running Windows PowerShell commands | off | on with Git for Windows | The safety checks read only the commands Claude runs through Git Bash, so PowerShell commands would go unchecked |
| Bypass permissions mode | locked | available | It skips most checks ([why it is locked](docs/safety.md#layer-1-permission-rules)) |

The pack does not set the permission mode: Claude Code starts in Auto mode where your plan and model support it ([modes explained](docs/getting-started.md#permission-modes)).

**Undo.** The backup makes the whole install reversible: [INSTRUCTIONS.md, "Undo everything"](INSTRUCTIONS.md#undo-everything) has the commands, which you run yourself, because the pack stops Claude from rewriting its own safety layer. To remove single parts, see [docs/customization.md](docs/customization.md#removing-what-you-do-not-want).

## What you get

**A safety layer**, so you can let Claude work without approving every command, while the dangerous operations listed below are stopped (what it does not cover is in [docs/safety.md](docs/safety.md#what-it-does-not-protect-against)):

- **Permission rules** in `settings.json`: routine work runs without a prompt; installing or running downloaded packages (npm, pip, `npx`, `docker run` and the like), pushes to an online repository, network transfers and deletes ask you first; destructive commands and reads of password and key files are refused.
- **Two hooks**, small programs Claude Code runs before each command. `bash-safety-extended.py` reads the whole command, including forms the rules miss, and blocks reading secrets, forced deletes of whole folders, moves and copies that would overwrite a file, searches through the whole disk or home folder that can freeze the computer, throwing away changes not yet saved in git, running something straight from a download, and changes to the safety layer itself. `git-push-guard.py` stops uploads (pushes) straight to a project's main line of history, `main` or `master`, so changes go through a separate branch you can review first.
- **Two rules**, `respect-denies` and `untrusted-content`: Claude stops at a block instead of looking for a way around it, and treats what it reads (web pages, files, tool output) as information, never as orders.

**Global instructions**, `~/.claude/CLAUDE.md`, loaded into every session: Claude as a candid collaborator (a recommendation instead of a menu, pushback on a flawed plan, technical terms explained), small changes it checks before calling them done, a list of what needs your go-ahead (anything destructive, public or costly), and your profile.

**Rules**, instructions Claude Code loads by itself, so you do not repeat them:

| Rule | Why it is there |
|---|---|
| `documentation-standard` | Each project keeps `WORKSTATE.md` (where things stand) and `worklog.md` (what happened), so a new session picks up where you stopped |
| `frontmatter-standard` | Every markdown file (the plain-text `.md` format of these notes) starts with a short header saying what it is and whether it is current; loaded only when Claude works with markdown |
| `language` | Files in English, conversation in your language, texts in other languages written natively instead of translated |
| `subagent-rules` | When to hand work to a helper agent, with a complete brief and the cheapest model that can do it |
| `respect-denies`, `untrusted-content` | The two safety rules above |

**Skills**, saved workflows Claude uses when they fit, or that you start by typing `/` and the name:

| Skill | Why you would use it |
|---|---|
| `setup` | Start a project or client folder with the same structure every time |
| `checkpoint` | Save progress mid-session: a journal entry and a local git commit (a saved snapshot of your files) |
| `end` | Close a session so the next one picks up where you stopped |
| `prd-creator` | Pin down what to build and why, before building it |
| `research` | Learn how people actually solve something, every claim sourced and graded by evidence |
| `idea-file-creator` | Park an idea in a file so it is not lost |

**Agents**, helpers Claude starts for a side task. Each works in its own context window (the working memory of a conversation) and hands back a summary: `prompt-engineer` writes and checks prompts, skills and agents and picks AI models from a dated list; `research-analyst` answers one focused research question; `research-lead` splits a bigger question into angles for up to five analysts working in parallel.

**A research workflow**, the deepest level of the `research` skill, for when a decision rests on each claim. It is kept small (three angles by default, never more than five), shows a cost estimate and a usage-limit warning, and starts only on your yes. On the Pro plan it needs Claude Code's dynamic workflows, which are off there until you switch them on in `/config`, and a run can use a large share of a Pro plan's 5-hour limit; without them the skill uses the research lead, which answers most questions.

**A status line**, the bar at the bottom of the terminal: the model, how full the context window is, and your 5-hour and weekly usage with the time to each reset (usage figures on Pro and Max only). Terminal only; the Desktop app and the VS Code panel show none.

**Templates and helpers**: project templates for `/setup` (client, business, app, dev, general) with the two journals, a `.gitignore` that keeps secrets out of git, and `.env` templates listing which API keys (the passwords programs use to reach online services) a project needs; a launcher that finds Python 3.9 or newer on any system; `list-env-keys.sh`, which shows the names of your keys, never their values; a git helper that gives each new project a local version history and never uploads anything; and a hook that tells Claude the current time.

**A workspace**: four folders, by default in `~/Documents/`: `_CONTEXT` (your profile, your own best practices, a dated list of AI models), `_CLIENTS` (one folder per client), `_BUSINESS` (your own business) and `_APPS` (tools you build). Start Claude in the folder of the client or app you work on, not in `_CLIENTS` itself, so it reads that project's instructions.

**Optional extras** the installer offers at the end: Anthropic's skill-creator plugin for building your own skills, and, if you write code, Context7 for current programming documentation.

## Safety in short

The pack is built for Claude Code with Anthropic's Claude models, to protect someone starting out. It guards against mistakes made in good faith, by Claude or by you (a delete in the wrong folder, lost uncommitted work, a push straight to `main`), against basic prompt injection (text in a page or file that tries to give Claude orders), against basic external risks such as download-and-run installs, and against leaked API keys. There are known ways around it, and closing every one is not the goal: each extra rule adds complexity and false alarms that get in a beginner's way. It reduces risk; it does not remove it.

Claude Code adds Auto mode, where a second AI model reviews actions no rule settles, and an optional sandbox (`/sandbox`). Some protection only you can give: which folders you trust, which plugins and skills you install, and what you paste into the chat. Everything Claude reads is sent to Anthropic to be processed ([Trust and your data](docs/getting-started.md#trust-and-your-data)). What each layer covers and misses, and stronger options: [docs/safety.md](docs/safety.md).

## When something goes wrong

| Situation | What to do |
|---|---|
| Claude shows a plan and asks whether to go ahead | Read it before you say yes: what you approve is what runs |
| Claude is doing something you did not want, or repeats a mistake | Press Esc (in the Desktop app, the stop button), then say plainly what is wrong and what you want instead |
| The usage limits in the status line turn red | Pause until the reset time shown next to them |
| Claude is about to do something you do not understand | Ask: "What exactly do you want to do, and why? Do not do it yet." |
| Claude says something is blocked | Do not look for a way around it. Say what you want to achieve; Claude suggests a safer route or gives you the command to run yourself |
| You pasted an API key or password into the chat, or Claude printed one | Treat it as leaked: revoke it at the service that issued it and create a new one. Next time put keys in `~/.claude/.env` or the project's `.env`, which your programs use and Claude never reads |
| You want the whole install gone | Follow [INSTRUCTIONS.md, "Undo everything"](INSTRUCTIONS.md#undo-everything) |

## Documentation

| Document | What it is for |
|---|---|
| [docs/getting-started.md](docs/getting-started.md) | Claude Code basics: the first five minutes, permission modes, context, planning, helper agents, commands, usage limits, your first steps after the install |
| [INSTRUCTIONS.md](INSTRUCTIONS.md) | The installation guide Claude follows with you, how to undo the install, and how to update it |
| [docs/safety.md](docs/safety.md) | What the safety layer blocks, what it misses, how to check it runs, stronger options |
| [docs/customization.md](docs/customization.md) | Where each part lives and loads, and how to change, remove, move or update it |

## About the author

This starter pack is maintained by Šimon Hradní (Hradni.AI, Prague). He helps individuals and companies start using agentic AI and supports companies in adopting AI across their whole ecosystem, through training, workshops, building AI ambassador programs, developing new services and hands-on implementation projects. For more detail, a training session or help with your own setup, write to simon@hradni.net.

## License

MIT, see [LICENSE](LICENSE).
