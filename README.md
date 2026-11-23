# The Technomancer: AI assistant setup

One file that gets a small business's team onto their own AI assistant: Claude (or
ChatGPT's Codex, Gemini, Grok), set up for their trade, their CRM and their phone system.
Made by [The Technomancer](https://thetechnomancer.ai). Built on
[Sterling Chin's MARVIN template](https://github.com/SterlingChin/marvin-template) (MIT).

## Install

About five minutes, Windows or Mac. You need a Claude (or ChatGPT) plan first.

1. Open the setup file you were sent.
   - **Windows:** double-click `Technomancer Setup.cmd`. If Windows shows a blue "protected your PC" box, click **More info**, then **Run anyway**.
   - **Mac:** unzip `Technomancer Setup (Mac).zip` and double-click the file inside. macOS refuses it the first time: open **System Settings → Privacy & Security**, find "Technomancer Setup.command was blocked", and click **Open Anyway**.
2. A setup page opens in your browser. It installs Claude Code, the Claude app, Chrome and the rest while you go through it.
3. Pick your assistant's name, color and voice, then tell it about the business: company name, trade, CRM and phone system.
4. Open the Claude app, sign in, click the **Code** tab, choose the folder the page shows, and type `/start`.

Running the setup file again is safe. It updates the tools and keeps your notes.

No setup file? Sign in at [thetechnomancer.ai/get-started](https://thetechnomancer.ai/get-started) to download yours. Each file works for 24 hours on one computer.

## The business screen

| Choice | What it does |
|--------|--------------|
| Company name and trade | Goes into the assistant's notes, its example prompts and its chat colors |
| CRM | Listed by trade (Roofr, JobNimbus, AccuLynx, ServiceTitan, Housecall Pro, Jobber and more) |
| Phone system | CallTrackingMetrics, CallRail, RingCentral, Dialpad, Quo and more |

A system with a live integration is **Connected** as soon as setup finishes: the
assistant gets a skill for it and reads it through the client's data bridge
(`TM_BRIDGE_URL` + `TM_BRIDGE_TOKEN`, carried by the setup file). Live today: Roofr and
CallTrackingMetrics. Every other system is **Pending**: setup saves its API key if one is
given (`<SYSTEM>_API_KEY` in `.env`) and the Technomancer finishes the connection. The
catalog is `INTEGRATIONS` in `install/wizard.py`; live skills live in `integrations/`.

## Company GitHub

On the GitHub step, setup asks whether the company already has a GitHub organization and
looks it up by the company's name.

- **First person:** creates the organization on GitHub's own page (setup opens it), then
  setup saves the company's trade, CRM and phone system to a private
  `<org>/assistant-settings` repository (`company.json`, with who set it up first).
- **Everyone after:** setup finds the organization and shows the person's username to send
  to an owner. The owner's assistant adds them (`github-team` skill). Setup accepts the
  invitation by itself, reads `company.json`, and offers to use the company's systems.
- Each person's assistant is backed up as a private repository in the organization.

No computer ever holds a key that can add people: only an owner can.

## Building a client's setup file

Keep a JSON file per client outside this repository (the fields are listed at the top of
`install/build-installer.py`), then:

```bash
python install/build-installer.py --client path/to/client.json
```

It writes `dist/<client>/Technomancer Setup.cmd` and `Technomancer Setup (Mac).zip`.
The bridge token is read from `.env` by the name the client file gives, never from the
client file, and never committed (`dist/` is ignored). A setup file with a token is for
that client only.

The automated test (`.github/workflows/installer.yml`) runs both install scripts on fresh
Windows and Mac machines on every push that touches `install/`, `integrations/`, `mods/`
or `.claude/`.

---

## What this starter adds on top of the vanilla template

- **The Boys protocol** (`.claude/agents/the-boys.md`) — Claude acts as PM; 5+ free AI workers (Gemini via Antigravity OAuth, Codex via ChatGPT) do the exploration, research, and drafting in parallel; a free Gemini reviewer synthesizes; you approve before any code lands.
- **Worker tooling** (`tools/agy-call.sh`, `tools/agy-extract.py`) — the wrapper that makes the Antigravity CLI usable headlessly.
- **Operational rules** baked into `CLAUDE.md` — CLI-first dispatch, failure handling, token economics, when to swarm vs. when to just do it.
- **Setup guide** — [`docs/the-boys-setup.md`](docs/the-boys-setup.md) gets the worker CLIs installed and authenticated in ~15 minutes.

Everything below is the standard MARVIN experience.

---

An AI assistant that remembers your conversations, tracks your goals, and helps you stay organized. Like having a personal chief of staff who never forgets anything.

## Why MARVIN?

MARVIN extends Claude Code with capabilities designed for getting things done:

- **Session continuity** - Pick up where you left off, even days later. Every conversation builds on the last.
- **Goal tracking** - Set work and personal goals, MARVIN monitors progress and nudges you forward.
- **Tool integrations** - Connect to Google Workspace, Microsoft 365, Atlassian, Slack, Linear, Notion, Telegram, and more.
- **Extensibility** - Add commands, agents, and skills tailored to your workflow. Create new capabilities with simple markdown files.
- **Thought partner** - MARVIN pushes back on weak ideas, asks probing questions, and helps you think through decisions. Not just a yes-man.

## Quick Start with Claude Code

1. Clone this repository:
   ```bash
   git clone <this-repo-url> marvin
   cd marvin
   ```

2. Open in Claude Code:
   ```bash
   claude
   ```

3. Ask MARVIN to help you set up:
   > "Help me set up MARVIN"

That's it. MARVIN walks you through the rest: your profile, goals, workspace location, and optional integrations.

## Getting Started with GitHub Copilot CLI

Want to use Copilot CLI to set up MARVIN quickly? Here's how:

### Prerequisites

- [GitHub Copilot CLI](https://cli.github.com/) installed and authenticated

### Quick Setup

Use these Copilot commands to get started:

```bash
# Navigate to your projects directory
gh copilot suggest "clone marvin template repository"

# Run the setup script
gh copilot suggest "run setup script for marvin"

# Start MARVIN
gh copilot suggest "start marvin AI assistant"
```

The `.marvin/setup.sh` script handles the MARVIN workspace setup: prerequisites, workspace creation, profile setup, and shell aliases. It does **not** install the worker CLIs for The Boys — do that separately via [`docs/the-boys-setup.md`](docs/the-boys-setup.md).

For additional integrations (Google Workspace, Slack, etc.), use:

```bash
gh copilot suggest "configure marvin integrations"
```

## What You Get

### Daily Workflow

Start your day with `/start` for a briefing: priorities, deadlines, progress toward goals. Work naturally throughout the day, MARVIN remembers everything. End with `/save` to save context for next time.

Between sessions, `/update` saves progress without ending.

> **Note on `/sync`:** this starter is a fork of the upstream MARVIN template. `/sync` pulls updates from the upstream template, which knows nothing about The Boys layer — review sync diffs before applying so they don't clobber `CLAUDE.md`'s Operational Rules or `.claude/agents/the-boys.md`.

### Commands

| Command | What It Does |
|---------|--------------|
| `/start` | Start your day with a briefing |
| `/save` | End session and save everything |
| `/update` | Quick checkpoint (save progress) |
| `/report` | Generate a weekly summary |
| `/commit` | Review and commit git changes |
| `/status` | Check integration & workspace health |
| `/sync` | Get updates from the template |
| `/help` | Show all commands and integrations |

### Integrations

MARVIN connects to tools you already use:

| Integration | What It Provides |
|-------------|------------------|
| [Google Workspace](.marvin/integrations/google-workspace/) | Gmail, Calendar, Drive |
| [Microsoft 365](.marvin/integrations/ms365/) | Outlook, Calendar, OneDrive, Teams |
| [Atlassian](.marvin/integrations/atlassian/) | Jira, Confluence |
| [Slack](.marvin/integrations/slack/) | Channel monitoring, posting |
| [Linear](.marvin/integrations/linear/) | Issue tracking |
| [Notion](.marvin/integrations/notion/) | Page reading, database queries |
| [Telegram](.marvin/integrations/telegram/) | Chat with MARVIN from your phone |
| [Parallel Search](.marvin/integrations/parallel-search/) | Web search capabilities |

Each integration includes setup instructions in its directory.

### Skills and Agents

MARVIN uses a `.claude/` directory structure for extensibility:

- **Commands** (`.claude/commands/`) - User-triggered workflows you invoke with slash commands
- **Agents** (`.claude/agents/`) - Specialized subagents MARVIN spawns for delegated work
- **Skills** (`.claude/skills/`) - Reusable capabilities Claude Code invokes contextually

Templates are included for each type. Just say "create a skill for X" and MARVIN generates the file.

## How It Works

MARVIN separates your workspace from the template:

```
~/marvin/                    Your workspace (your data lives here)
├── CLAUDE.md               Your profile and preferences
├── state/                  Your goals and priorities
├── sessions/               Your daily session logs
└── ...

~/marvin-template/          Template (get updates here)
├── .marvin/                Setup scripts and integrations
├── .claude/                Command and agent templates
└── ...
```

Your workspace holds all personal data. The template provides updates. Run `/sync` from your workspace to pull new features without overwriting your data.

## Migrating from Older Versions

If you were using MARVIN before the workspace separation:

```bash
cd marvin-template
./.marvin/migrate.sh
```

The script copies your profile, goals, sessions, reports, and custom skills to a new workspace. Nothing is deleted from your old installation. Verify the new workspace works, then clean up the old one.

## Contributing

MARVIN welcomes contributions in three areas:

1. **Integrations** - Add support for new tools. See [.marvin/integrations/CLAUDE.md](.marvin/integrations/CLAUDE.md) for patterns and security requirements.
2. **Commands, agents, skills** - Extend MARVIN's capabilities. Templates are in `.claude/commands/`, `.claude/agents/`, and `.claude/skills/`.
3. **Bug fixes** - Found an issue? Submit a PR with the fix and a test case.

Fork the repo, create a branch, and submit a PR. All contributions are reviewed.

## About

MARVIN is named after the Paranoid Android from The Hitchhiker's Guide to the Galaxy.

Created by [Sterling Chin](https://sterlingchin.com).
