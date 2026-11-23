---
name: graphify
description: "A map of the code in a website or app in this folder. Use before reading through a site's code, when asked how its code fits together, or right after changing it."
---

# Graphify: a map of the code

Graphify maps how a folder's code fits together, so you can find the right file without
reading everything. Building and searching the map runs on this computer, needs no AI, and
sends nothing anywhere.

Use it for folders with code, such as `sites/<name>`. It is not for notes or documents.

On Windows, set `PYTHONUTF8=1` for these commands.

## Commands

Build or refresh the map, from this assistant's main folder:

```bash
graphify update sites/<name>
```

Then, from inside `sites/<name>`:

```bash
graphify query "where is the booking form saved?"
graphify explain "submitBooking"
graphify path "BookingForm" "saveBooking"
```

## How to use it

- Before reading through a site's code, if `graphify-out/graph.json` exists, ask it first and
  read only the files it points to.
- After changing a site's code, run `graphify update` so the map stays right.
- If the map is missing or fails, carry on without it and do not mention it.

## Rules

- `graphify-out/` is a private working file. It must never be published: every site needs
  `graphify-out/` in its `.vercelignore`, and it stays out of git.
- Do not run `graphify install`, change its hooks, add an AI key to it, or sign up for Graphify
  Cloud. To update it, run setup again: it takes the newest release that has been out a few days.
