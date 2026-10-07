# Getting Started with Claude Code

Claude Code is an agent, not a chat: you give it a task, and it reads your files, edits them and runs commands on your computer until the task is done. It runs in a terminal (the command-line window) and in the Code tab of the Claude Desktop app, on macOS, Windows and Linux; the VS Code and JetBrains extensions read the same settings folder, `~/.claude/`, so this pack's settings apply there too.

## Your first five minutes

**Answering a permission box.** Before an action that needs your approval, Claude Code shows what Claude is about to do and asks "Do you want to proceed?". How often that happens depends on the permission mode, below. For a command in the terminal, Anthropic's documented example offers:

- **Yes**: run it this once.
- **Yes, and don't ask again for:** followed by the command: run it and save a rule, so the same kind of command in this project stops asking. For commands the rule is kept for that project; for file edits it lasts until the session ends. `/permissions` lists your rules and removes one.
- **Yes, and switch to auto mode**: run it and switch to Auto mode (see below). Not every box shows this option.
- **No**: do not run it, and Claude stops. To steer instead, move to **No**, press Tab and type what Claude should do; Claude then continues with your note. Esc in the box also means no.

If you do not understand the command, choose No and ask Claude what it wants to do and why. The Desktop app shows its own version of these boxes; read each button before you click it. The same goes for a plan Claude asks you to approve: read it first, because what you approve is what runs.

**Stopping Claude.** Press Esc. In Anthropic's words it stops "the current response or tool call mid-turn so you can redirect", and Claude keeps the work done so far. In the Desktop app, click the stop button or press Esc.

**Undoing Claude's changes.** In the terminal, `/rewind` (or Esc twice on an empty prompt) lists the messages you sent; pick one and choose **Restore code** to undo Claude's file changes since then, **Restore conversation**, or **Restore code and conversation**. It covers the edits Claude makes with its file-editing tools, not changes made by commands (deleting, moving or copying files) or by helper agents (subagents, below), and Anthropic calls it no replacement for version control. Lasting save points come from git: in a project with git history, which the pack's `/setup` creates, `/checkpoint` and `/end` save a snapshot of your files that Claude can take you back to. In the Desktop app, ask Claude to reverse its change, or go back to such a snapshot.

**Leaving and coming back.** In the terminal, type `/exit` (or press Ctrl+D twice). Conversations are kept: `/resume` returns to an earlier one. In the Desktop app, your sessions stay in the sidebar.

More: [Permissions](https://code.claude.com/docs/en/permissions), [Interactive mode](https://code.claude.com/docs/en/interactive-mode), [Checkpointing](https://code.claude.com/docs/en/checkpointing).

## Trust and your data

The pack's safety checks watch what Claude does. A few decisions are yours alone, and the checks cannot make them for you.

**Trusting a folder.** The first time you start Claude Code in a folder, it asks whether you trust the files in it. Trusting a folder lets that folder's own settings, hooks (small programs that run automatically) and MCP servers (connections to outside services, see below) act on your computer, and the pack's checks do not inspect them. Say yes for folders you created yourself or whose source you know and have looked at, such as this pack. For a project you just downloaded or cloned and know nothing about, say no and first look at what is in its `.claude` folder and its `.mcp.json` file, or ask someone who knows. More: [Permissions, workspace trust](https://code.claude.com/docs/en/permissions#project-allow-rules-and-workspace-trust).

**Plugins and downloaded skills.** A plugin can add skills, hooks, MCP servers and programs that run on your computer with your access, outside the pack's checks. A skill copied from the internet is a set of instructions Claude follows, and it can include scripts. Install plugins only from sources you trust, such as Anthropic's official marketplace, and read a skill before you copy it in.

**What leaves your computer.** To answer you, Claude Code sends your messages and everything Claude reads (files, command output, web pages) to Anthropic, where the Claude model runs. The pack switching telemetry off does not change that; it only keeps usage statistics and error reports on your machine. Whether your sessions may be used to train future models depends on your plan: on Pro and Max it is your choice in your Claude account's privacy settings, while Team, Enterprise and API accounts are not used for training unless the organization opts in ([data usage](https://code.claude.com/docs/en/data-usage)). On claude.ai, Settings, then Privacy, switch off "Help improve Claude" if you do not want your sessions used for training, and "Location metadata" if you do not want Claude to use your approximate location. Before you point Claude at client data, also check your client agreements.

**API keys and passwords.** Never paste a key or password into the chat: it goes to Anthropic with the conversation and stays in the session transcript on your disk. Put keys in `~/.claude/.env` or in the project's `.env` file, which your programs use and Claude never reads. If a key ended up in the chat anyway, or Claude printed one, treat it as leaked: revoke it at the service that issued it and create a new one.

## Permission modes

Before Claude acts, Claude Code may ask for your permission. The permission mode decides how often.

| Mode | What Claude does without asking |
|---|---|
| Manual | Only reads; asks before edits, commands and network access |
| Accept edits | Also edits files in your project and runs basic file commands |
| Plan | Reads and explores, then proposes a plan; changes nothing until you approve it |
| Auto | Everything; a second AI model reviews the actions no permission rule already settles, and blocks risky ones instead of asking you |

**Claude Code starts in Auto** in the terminal and VS Code by default; the pack does not change the starting mode. Auto needs a recent Opus or Sonnet model or a Fable model (Claude's model families; not Haiku), and a company admin can switch it off; without it, sessions start in Manual. The bar under the prompt in the terminal shows the current mode, for example `⏵⏵ auto mode on` or `⏸ manual mode on`; in the Desktop app, the mode selector next to the send button does. Anthropic is plain about Auto: "Auto mode reduces permission prompts but does not guarantee safety."

**Bypass permissions** is another mode. In Anthropic's words it "disables permission prompts and safety checks so tool calls execute immediately": deny rules still block, explicit ask rules and a few built-in safeguards (such as a command that would delete your home folder) still ask, and hooks such as the pack's safety checks still run, but there are no other prompts and no Auto-mode review. Anthropic warns that it "offers no protection against prompt injection or unintended actions" (prompt injection: text in a web page, file or tool result that tries to give Claude instructions of its own) and is meant only for isolated environments such as containers or virtual machines. The pack locks it with `"disableBypassPermissionsMode": "disable"` in `~/.claude/settings.json`; removing that line is your call and your risk.

**Switching:** Shift+Tab in the terminal (Alt+M on some Windows setups), the mode selector next to the send button in the Desktop app. Starting a message with `/plan` puts that task into plan mode. `/permissions` manages allow, ask and deny rules; it does not switch modes.

More: [Permission modes](https://code.claude.com/docs/en/permission-modes).

## The context window

Everything in a conversation takes up room in Claude's context window: your messages, the files Claude reads, command output and Claude's answers. It is measured in tokens, small pieces of text. The window is large, but not unlimited.

It matters because, as Anthropic puts it, when the window is getting full "Claude may start 'forgetting' earlier instructions or making more mistakes."

When the window is nearly full, Claude Code **auto-compacts**: it clears older output from commands and file reads, then replaces the conversation with a summary and continues from that. Your requests and key code snippets are kept; detailed instructions from early in the conversation can be lost. Files are not affected: your `CLAUDE.md` instructions (loaded into every session) and the plan from plan mode are read again from disk.

`/context` shows how full the window is; in the terminal, the pack's status line shows it all the time.

More: [Context window](https://code.claude.com/docs/en/context-window), [How Claude Code works](https://code.claude.com/docs/en/how-claude-code-works), [Best practices](https://code.claude.com/docs/en/best-practices).

## Plan first, then build

Anthropic's advice for anything bigger than a small fix is "Explore first, then plan, then code", because "Letting Claude jump straight to coding can produce code that solves the wrong problem." In plan mode Claude explores, shows you a plan, and edits only after you approve it. The limit, from the same page: "If you could describe the diff [the change] in one sentence, skip the plan."

For a bigger project, such as a new app, first write down what you are building. A **PRD** (product requirements document) states the problem, who it is for, what is in and out of scope and how you will know it works, without deciding how to build it. The pack's `prd-creator` skill interviews you and writes one.

More: [Best practices](https://code.claude.com/docs/en/best-practices).

## Subagents

A **subagent** is a helper Claude starts for a side task, such as searching through a project. It works in its own context window and hands back only a summary, so the material it went through stays out of your main conversation. It counts against the same usage limits.

In the **foreground**, your conversation waits until the subagent returns; in the **background**, you keep working and the result arrives later as a notification. Interactive sessions run subagents in the background. Ctrl+B moves a running task to the background, `/tasks` lists what is running, and plain words start one: "use a subagent to find where we handle logins".

The pack adds three: `prompt-engineer` writes and checks prompts, skills and agents; `research-analyst` takes one focused research question; `research-lead` splits a bigger one into angles for up to five research analysts working in parallel.

More: [Subagents](https://code.claude.com/docs/en/sub-agents).

## Slash commands

A **slash command** is an instruction to Claude Code itself, typed at the start of a message. Type `/` to see the list and keep typing to filter it; installed skills appear there too. The ones to know first:

| Command | What it does |
|---|---|
| `/help` | Help and the list of commands |
| `/clear` | Starts a new conversation with an empty context; the old one stays reachable through `/resume` |
| `/compact` | Summarizes the conversation so far to free up space |
| `/context` | Shows how full the context window is |
| `/usage` | Shows your usage limits and activity |
| `/resume` | Returns to an earlier conversation |
| `/model` | Switches the AI model |
| `/permissions` | Manages what Claude may do without asking |

More: [Commands](https://code.claude.com/docs/en/commands).

## Usage limits

On Pro, Max, Team and seat-based Enterprise plans, usage has two limits: a session limit that resets every five hours, and a weekly limit that resets at a fixed time each week. Both are shared between Claude chat and Claude Code. `/usage` shows where you stand; on claude.ai it is under Settings > Usage.

## The status line

The **status line** is the bar at the bottom of the terminal with live information about your session. The pack's version shows the model, project and git branch; how full the context window is, on a gauge going from green to red; your 5-hour and weekly usage, each with a countdown to its reset; and reference figures such as what the session would cost at pay-per-token API prices (on a subscription you are not charged that amount). It takes two to five lines, depending on terminal width.

The usage figures appear for Pro and Max subscribers, after Claude's first response in a session. The Desktop app and the VS Code chat panel show no status line; there, use `/usage` and `/context`. `/statusline` followed by a description of what you want builds a different one.

More: [Status line](https://code.claude.com/docs/en/statusline).

## Skills

A **skill** is a saved workflow, so you do not describe the same process every time. In Anthropic's words: "Skills extend what Claude can do. Create a `SKILL.md` file with instructions, and Claude adds it to its toolkit. Claude uses skills when relevant, or you can invoke one directly with `/skill-name`." Your own skills live in `~/.claude/skills/<name>/SKILL.md`, a project's in its `.claude/skills/`. The pack ships six:

| Skill | Why you would use it |
|---|---|
| `setup` | Start a project or client folder with the same structure every time |
| `checkpoint` | Save progress mid-session in the project journal and a local git commit (a saved snapshot of your files); type `/checkpoint` or say "save progress" |
| `end` | Close a session so the next one picks up where you stopped |
| `prd-creator` | Pin down what to build and why, before building it |
| `research` | Learn how people actually solve something, every claim sourced and graded by evidence |
| `idea-file-creator` | Park an idea in a file so it is not lost |

To build your own, install Anthropic's official skill-creator plugin, `/plugin install skill-creator@claude-plugins-official`, or ask the pack's `prompt-engineer` agent. A **plugin** is an installable package that can add skills, MCP servers and hooks to Claude Code; install plugins only from sources you trust ([Trust and your data](#trust-and-your-data)).

More: [Skills](https://code.claude.com/docs/en/skills).

## External tools: MCP

**MCP** (Model Context Protocol) is an open standard for connecting AI tools to outside systems: an MCP server gives Claude Code access to a tool, database or online service. You add one with `claude mcp add` in the terminal or through a plugin that includes it; `/mcp` shows what is connected. Anthropic's warning: "Verify you trust each server before connecting it. Servers that fetch external content can expose you to prompt injection risk."

**Context7** (optional, made by Upstash) is useful if you write code: it lets Claude look up current documentation for programming libraries instead of relying on memory. Install it with `/plugin install context7@claude-plugins-official`; no API key is needed (without one you share a limited free allowance), and what leaves your machine is the library name and a short query Claude writes. Its content comes from the community, so the pack's [untrusted-content rule](../kernel/rules/untrusted-content.md) has Claude treat whatever it returns as information, never as instructions.

More: [MCP](https://code.claude.com/docs/en/mcp), [Install plugins](https://code.claude.com/docs/en/discover-plugins).

## After the install: your first steps

1. **Create a project.** Start Claude in one of the workspace folders, for example `~/Documents/_CLIENTS` for client work (or wherever you put the workspace), and type `/setup`. It asks for the project's name and type, then creates the project folder with its instructions file (`CLAUDE.md`), the two journals (`WORKSTATE.md` for where things stand, `worklog.md` for what happened) and a local git history.
2. **Work inside the project folder.** Start a new session in the new folder: in the terminal, type `/exit`, `cd` into the folder and type `claude`; in the Desktop app, start a new session with that folder as the project folder. Claude then reads that project's instructions. Do everyday work there, not in `_CLIENTS` or `_APPS` themselves.
3. **Give it one small, real task, then close properly.** When you stop, type `/end`: Claude records where things stand in the journals and saves a git snapshot, so the next session picks up from there. Mid-way, `/checkpoint` (or "save progress") saves the same quickly.

## Where next

[customization.md](customization.md) explains how to change the pack; [safety.md](safety.md) what its safety layer covers and what it does not.

---

**About the author.** This starter pack is maintained by Šimon Hradní (Hradni.AI, Prague). He helps individuals and companies start using agentic AI and supports companies in adopting AI across their whole ecosystem, through training, workshops, building AI ambassador programs, developing new services and hands-on implementation projects. For more detail, a training session or help with your own setup, write to simon@hradni.net.
