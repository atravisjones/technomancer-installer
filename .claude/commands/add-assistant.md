---
description: Add another AI you already pay for (ChatGPT, Gemini or Grok) to help this assistant
---

# /add-assistant - Add Another AI to the Team

Another AI can give a second opinion, take on research, or pick up when this one reaches its
usage limit. It reads the same notes. Each one needs its own paid plan.

## Instructions

### 1. Ask which one
ChatGPT (`codex`), Gemini through Antigravity (`agy`), or Grok (`grok`). If they do not pay for
any of them, say none is needed and stop.

### 2. Say what will change, and get a yes
It installs that company's tool and lets it work in this folder without stopping to ask each
time. Go on only after they agree.

### 3. Add it
Run this from the assistant's folder, with their choice in place of `codex`:
```bash
uv run --quiet --no-project --python 3.12 "$(cat .marvin-source)/install/wizard.py" --add-assistant codex --folder .
```
It prints one line of JSON.
- `"ok": true`: tell them to double-click the file named in `open`, in this folder, and sign in
  with the account named in `account`. Their first sign-in happens there.
- `"ok": false`: say what `error` or `note` says in plain words. If the setup files are missing,
  tell them to run their setup file again from their account page.

## Rules
- Never ask for a password or key in this chat.
