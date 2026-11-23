---
description: Use this assistant on another computer, and move its saved keys with a one-time code
---

# /add-computer - Use This Assistant on Another Computer

The other computer gets this assistant's notes through the person's GitHub. Keys never go in
GitHub as readable text: they are locked with a one-time code that only this computer shows.

## Instructions

### 1. Save first
```bash
uv run --quiet --no-project --python 3.12 .claude/tools/computers.py push
```
- `ok`: go on.
- `no-backup`: this assistant has no GitHub copy yet. Tell the person to run setup again and finish the GitHub step, then stop.
- `offline` or `signed-out`: say what is wrong in one line, then stop.
- `conflict`: `files` changed on both computers. Nothing was overwritten. For each file, show the
  person the difference in plain words (`git diff HEAD origin/<branch> -- <file>`) and ask which to
  keep: this computer's, the other computer's, or both. Never choose for them. Then run
  `uv run --quiet --no-project --python 3.12 .claude/tools/computers.py resolve "<file>=mine"` (or `=other`, or `=both`), naming every file.
- Never use `git push --force`, `git reset --hard` or `git checkout --` on these notes.

### 2. Lock the keys and show the code
```bash
uv run --quiet --no-project --python 3.12 --with cryptography==50.0.2 .claude/tools/computers.py keys-send
```
- `ok`: a page opened in the browser with the code. Go to step 3.
- `nothing`: there are no keys to move. Go to step 3 and leave out the code.
- `error`: tell the person its `message`, then stop.

### 3. Tell the person what to do
Say this in plain words:
1. On the other computer, open the same install file you used here.
2. Choose **I already set this up on another computer**.
3. Sign in to the same GitHub account.
4. If a code page opened here, type that code into setup. It works once and ends in 24 hours.

## Rules
- Never read, print or summarize `.env`.
- Never ask for the code in this chat. If the person pastes it here anyway, that code is no longer
  private: run `keys-cancel` with the same command, then `keys-send` to make a new one.
