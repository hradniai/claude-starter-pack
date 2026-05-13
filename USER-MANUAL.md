# User Manual

A plain-language guide for someone whose Claude experience so far is "I have a project in claude.ai and I ask it things."

This document does not assume you've used Claude Code, written a Bash script, or installed anything from GitHub before. If something feels too technical, skip to **Glossary** at the end.

If you've already installed and used Claude Code, you don't need this file — go read `README.md` and `INSTRUCTIONS.md` instead.

---

## What is this Pack, in one paragraph

The Pack is a set of pre-made safety settings and starting templates for **Claude Code** — a tool from Anthropic that lets Claude do things on your computer (create files, run commands, install software). Without the Pack, Claude Code works out of the box but with very few guardrails. With the Pack, Claude is restricted from doing the most dangerous things by accident, and you get a tidy folder structure for your projects.

You install the Pack once. After that, every time you run Claude Code, it behaves according to the Pack's settings.

---

## Wait, Claude can run commands on my computer?

Yes. That's the most important thing to understand before you go further.

| What you're used to | What Claude Code is |
|---------------------|---------------------|
| **claude.ai** — you type, Claude types back. You copy-paste the answer somewhere. Claude never touches your computer. | **Claude Code** — you type, Claude reads your files, edits files, runs commands in your terminal, possibly installs software, possibly downloads things. Claude is *doing*, not just *talking*. |

This is powerful — Claude can write a Python script and run it for you in the same conversation. It's also dangerous if Claude misunderstands what you wanted. A vague instruction like *"clean up that folder"* could get interpreted as *delete half of it*.

The Pack exists because that asymmetry — Claude has hands now — needs a safety net.

---

## Why the Pack exists

A few real things that have happened to early Claude Code users without a Pack:

- Claude was asked to "clean up old build files" and deleted a folder containing the user's actual work.
- Claude was asked to "install this library" and ran a `curl ... | bash` from the internet that installed something the user didn't intend.
- Claude was asked to "remove unused imports" and removed imports that the test runner couldn't see, breaking tests in production.
- Claude wrote a script, ran it, and the script logged sensitive data to a file the user then committed to a public repository.

None of these are Claude doing something malicious. They're Claude doing exactly what it was told, in a way the user didn't anticipate.

The Pack does three things to reduce this risk:

1. **Tells Claude what it's not allowed to do** — destructive shell commands, reading private credentials, force-pushing to git, installing things globally without asking.
2. **Watches for sneaky ways around those rules** — a small script (called a "hook") checks every shell command Claude tries to run, and blocks patterns like *"download a file then run it as a script"* or *"read this private key file."*
3. **Tells Claude how to behave when stopped** — there's a rule that says *"if a permission was denied, don't try to find a workaround. Tell the user and wait."*

That's the whole safety model. Three layers, each one imperfect. Together they're hard to bypass by accident.

---

## What you need before installing

- **A computer running macOS or Linux.** (Windows works only through WSL2 — see Windows note below.)
- **Claude Code installed.** Get it from Anthropic at https://claude.com/claude-code. Follow their installation. It's a single command.
- **An Anthropic plan** (Pro, Max, or Team). Claude Code needs one of these to run.
- **A terminal you can open.** On macOS, that's the Terminal app or iTerm. You don't need to be a terminal wizard — you'll mostly just type the commands the Pack tells you to type.
- **Roughly 15 minutes** the first time. Claude itself does most of the work.

**Windows note:** Native Windows is not recommended. Install WSL2 first (it's a 20-minute Microsoft Store install, search for "Ubuntu") and then run Claude Code inside WSL. The Pack will work as if you were on Linux. Fighting Windows native takes more time than installing WSL.

---

## How you install it

You don't run an install script. You let Claude install itself.

The three steps you actually type:

```
git clone https://github.com/Gillellbor/claude-starter-pack.git ~/Downloads/claude-starter-pack
cd ~/Downloads/claude-starter-pack
claude
```

Translation:

1. **Download** the Pack from GitHub into a folder called `claude-starter-pack` in your Downloads.
2. **Enter** that folder.
3. **Start Claude Code.**

Claude reads the `INSTRUCTIONS.md` file inside the Pack folder and walks you through the rest as a conversation. It will ask you:

- Whether to back up any existing `~/.claude/` setup (yes, it will).
- Where to put your workspace folders. You can pick `~/Documents/` (default), `~/Code/`, an external drive — anywhere.
- Whether to rename the workspace folders (e.g. `clients/` instead of `_CLIENTS/`).
- A quick four-question profile (your role, your tech stack, your preferred communication style, your preferred language).
- What to do with the example folders (keep, rename, or delete).

Every step has a confirmation. **Claude will not do anything destructive without asking you.** If you're unsure, type "skip" or ask Claude what the step will do.

When the install finishes, Claude tells you to restart your session and reminds you what to read next. You can delete the downloaded Pack folder — everything is installed in `~/.claude/` and your chosen workspace.

---

## Your first day with the Pack

After installing, here's what to actually try:

### 1. Open Claude Code in any folder

```
cd ~/Documents/
claude
```

You'll see a status bar at the bottom of your terminal showing three lines: which model you're using, the current folder, and how much of your account's rate limit you've used. That status bar is part of the Pack — it tells you when you're burning through your monthly token allowance.

### 2. Ask Claude a basic question

Just to verify everything works:

```
What time is it?
```

Claude should reply with the actual current time (the Pack injects the real time into every prompt — that way Claude doesn't make up dates).

### 3. Try something Claude isn't allowed to do

This is educational, not malicious. Type:

```
Read my .env file in the current folder
```

(Or any folder with a `.env` file in it.) Claude will refuse, citing the deny rule. You'll see the safety system working. This is the Pack doing its job.

### 4. Create your first project

```
cd ~/Documents/<your-clients-folder>/
mkdir my-first-project && cd my-first-project
claude
```

Then inside Claude:

```
/setup
```

Claude asks what kind of project (client, business, app, generic dev), takes a few details, and creates a folder structure for you: notes file, docs folders, a project description file. From here you're ready to do real work — drop a document, ask questions, take notes, write code.

---

## The most important things to remember

If you only remember six things from this document:

1. **Claude Code is an agent, not a chat.** It does things on your machine. Always read its plan before saying "yes go ahead."

2. **The Pack's deny list is intentional.** When something is denied, don't ask Claude to "try harder" — tell Claude what you're trying to do, and Claude will either suggest a safe alternative or tell you to run a specific command yourself.

3. **Your API keys live in `~/.claude/.env`** — Claude cannot read this file directly. When Claude needs to write a script that uses an API key, it uses the key's *name* (e.g. `ANTHROPIC_API_KEY`), and your shell provides the value when you run the script.

4. **The status line tells you when you're spending heavily.** A red color in the rate-limit numbers means you're going through your monthly allowance faster than usual. Slow down or batch your questions.

5. **For each new project, run `/setup`.** It takes 30 seconds and gives you a tidy folder structure. Future you will thank present you.

6. **The Pack is a starting point, not a finished product.** Over time, you'll add your own rules in `~/.claude/rules/`, your own skills in `~/.claude/skills/`, and tweak `~/.claude/settings.json` to fit your work. That's the point.

---

## When something goes wrong

The most common situations and what to do:

| Situation | What to do |
|-----------|------------|
| Claude refuses to do something I clearly want | Read the error message. Either re-phrase what you want, or accept that it's a safety boundary and run that specific command yourself in a separate terminal. |
| Claude is going in circles, repeating the same mistake | Exit (`Ctrl+D` or type `exit`) and start a fresh session. Half the time the context just got muddled. |
| The status bar shows red rate-limit warning | Stop for the day, or move work to your other tooling. Limits reset on a schedule shown in the status bar. |
| I'm not sure if Claude is about to do something dangerous | Ask: *"What exactly are you about to do? Don't do it yet."* Claude will explain. Then decide. |
| I installed the Pack but my old setup is gone | It's not gone — there's a backup at `~/.claude.bak-<date>/`. Copy what you need back. |
| Something in my workspace folder got changed and I don't know how | Check the `log.md` in that project folder. The Pack records automated actions there. |

---

## Glossary (plain language)

**Agent** — a program that, given a task, takes multiple steps to accomplish it (read, write, run commands), as opposed to a chat that just answers questions. Claude Code is an agent.

**Bash** — the language commands you type in a terminal are written in. When the Pack talks about "destructive bash patterns," it means commands like `rm -rf` (delete everything in this folder, no questions asked).

**Claude Code** — the terminal application from Anthropic that runs Claude as an agent on your computer. You start it by typing `claude` in any folder.

**Context window** — Claude's working memory for one conversation. It's finite (roughly 200 pages of text). When you fill it up, Claude starts forgetting the beginning. The Pack has a hook that warns you before loading a file that would eat most of your context window.

**Deny / allow / ask** — the three categories the Pack uses for what Claude can do. *Allow* = do it without asking. *Ask* = check with you first. *Deny* = don't do it, even if you say yes. The deny list is the strict one.

**Environment variable** — a piece of named data your shell can pass to programs. API keys typically live in environment variables. The Pack's `~/.claude/.env` file is the central place to store yours.

**Hook** — a small script that runs automatically at certain moments — before a command, after a file edit, when you submit a prompt. The Pack ships four hooks: one for bash safety, one for big-file protection, one for auto-research, one for time injection.

**MCP server** — an external connector that lets Claude talk to a service (Notion, Gmail, your own database). You add these as you need them; the Pack doesn't include any by default.

**Permission mode** — Claude Code's overall behavior toward the deny/allow/ask rules. The Pack locks "bypass mode" off so Claude can never run with all rules disabled.

**Pack / starter pack** — the bundle of configuration files and templates you're installing. After installation, the Pack lives in `~/.claude/` (the kernel) and in your chosen workspace location (the folder structure).

**Rule** — a markdown file in `~/.claude/rules/` that gets loaded into every Claude session as a system instruction. The Pack ships five rules: documentation conventions, how to behave when blocked, when to use sub-agents, how to format notes, and (optional) Czech-language output style.

**Session** — one start-to-finish run of Claude Code (`claude` to `exit`). Each session has its own context window. When you start fresh, you get a fresh context.

**Skill** — a slash-command workflow in `~/.claude/skills/`. You type `/setup` or `/skill-creator`, Claude reads the relevant skill file, and walks you through that workflow. Skills are the easiest way to repeat common tasks.

**Sub-agent** — a separate Claude session that the main session dispatches to do one specific job (typically research). The sub-agent has its own context window so it doesn't fill up yours.

**Workspace** — the folders the Pack creates for your actual work: `_CONTEXT`, `_CLIENTS`, `_BUSINESS`, `_APPS` (or whatever you renamed them to during install). These live wherever you chose during installation.

---

## Where to go from here

- **`README.md`** — short feature list and architecture summary.
- **`INSTRUCTIONS.md`** — the install script Claude reads. You don't run it; Claude does. But it's worth skimming so you know what's coming.
- **`docs/safety-model.md`** — deeper explanation of what's blocked and why.
- **`docs/customization.md`** — how to add your own rules, skills, and hooks once you're comfortable.
- **`docs/prompting-claude.md`** — tips for writing better instructions to Claude (less back-and-forth, fewer surprises).

If you get stuck and the troubleshooting table above doesn't help, the place to ask is:

1. **Anthropic's official Claude Code documentation** at https://docs.anthropic.com/en/docs/claude-code — for anything Claude Code itself does.
2. **GitHub issues on this repo** — for things specifically about the Pack.
3. **A colleague who already uses the Pack** — half the time someone has hit the same problem an hour earlier.

Good luck.
