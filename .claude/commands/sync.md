---
description: Get the latest updates to this assistant
---

# /sync - Get Updates

Updates bring new commands, skills and fixes. They never touch the person's notes (`state/`,
`sessions/`, `reports/`, `content/`), `.env`, or their own part of `CLAUDE.md`. A setup file the
person (or you) changed is kept as it is and reported, never replaced without a yes.

## Instructions

### 1. Get the newest files (this checks the plan)
```bash
uv run --quiet --no-project --python 3.12 .claude/tools/get-updates.py
```
If `uv` is not found, run the same file with `python3`, or `python` on Windows. It prints one line of JSON.
- `"ok": true`: go to step 2.
- `"error": "offline"`: tell the person the `message`, then go to step 2 with the copy already on this computer.
- Any other error: tell the person the `message`, say that everything they already have keeps working, and stop.

### 2. Apply them
```bash
uv run --quiet --no-project --python 3.12 .claude/tools/apply-updates.py
```
If `uv` is not found, run the same file with `python3`, or `python` on Windows. It prints one line of JSON.

### 3. Tell the person, in plain words
- If `ok` is false, say what `error` says. Nothing was changed.
- Say which version they are on now (`to`). If `from` and `to` match and `added` and `updated` are
  empty, say they were already up to date and stop.
- List the `whatsNew` lines.
- Say how many things were added and refreshed. Name commands as `/name` (`$name` in ChatGPT).
- For each file in `kept`: it was changed on this computer, so the update left it alone. Offer to
  show the difference between it and the new version at `<template>/<file>` (`template` is in the
  JSON), and to switch to the new one. Only switch the files they say yes to.

## Rules
- Never use `git push --force`, `git reset --hard` or `git checkout --` on these notes.
- Never read, print or summarize `.env`.
