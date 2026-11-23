---
description: Put a web page or app online with Vercel, with a Supabase database when it needs one
---

# /publish - Put it online

The person wants something on the web: a page, a form, a small tool, a dashboard. Build
it, put it online with Vercel, and give them the link. If it needs to save data, give it a
Supabase database. Plain words throughout: they do not need to know how it works.

## Rules that are never skipped

- **Ask before anything goes public the first time.** Show what it looks like (open the
  local copy in Chrome, or describe it), say the address it will get, and wait for a yes.
  Later updates to the same site only need a one-line heads-up.
- **Secrets never go in the code or in git.** Keys live in `.env` here and in Vercel's
  environment settings (`vercel env add`). Before any commit, check that `.env*` files and
  `.vercel/` are ignored (`git check-ignore`). Only Supabase's public "anon" (publishable) key
  may ever reach a browser. The service role (secret) key stays on the server side.
- **Every Supabase table gets Row Level Security turned on when it is created,** with a
  policy that lets people see and change only what they should. A table without RLS is
  open to anyone on the internet who has the page.
- **Back up before you delete or change data.** Before any `delete`, `drop`, `truncate` or
  bulk `update`, save a copy of the rows it touches, and say what will change. Never use an
  upsert that could blank out columns it was not given.
- **Never deploy from a git worktree or a copy of the folder:** only from the site's own
  folder, on its main branch.
- **Never type a password, card number or payment detail for the person.** Sign-ups and
  upgrades are theirs to click.

## 1. Check the tools

```bash
vercel whoami
supabase projects list
```

- Not signed in to Vercel: run `vercel login`. It prints a link: open it in Chrome for them
  and tell them to approve it, then carry on when it finishes.
- Not signed in to Supabase (only needed if the site saves data): its sign-in needs a real
  terminal. Open a new terminal window for them, have them run `supabase login` there, and
  carry on when `supabase projects list` works. Never ask them to paste a token into this chat.
- A tool missing: tell them in one line to run setup again (it reinstalls only what is
  missing), and stop.

## 2. Make the site

- Each site gets its own folder: `sites/<short-name>/` inside this folder, lowercase with
  dashes (for example `sites/spring-promo`).
- Start simple. One page with no build step (plain `index.html`, CSS and a little
  JavaScript) is right for most requests. Use a framework such as Next.js only when the
  person needs logins, many pages or server code.
- Make it look professional and work on a phone. Use the company's name, colours and logo
  if `CLAUDE.md` or the company website gives them.
- If this folder is backed up to GitHub, commit the site with the rest. If the company has
  its own GitHub (`.company-github`), a site that will grow can get its own private
  repository there; ask first.

## 3. A database, if it needs one

Only when the site must save or share data (form entries, bookings, a list people edit):

1. Make a Supabase project, or reuse one this person already made for the same purpose
   (`supabase projects list`). The free plan allows two projects, so prefer one project
   with several tables over a new project per site. Pick the region closest to them.
2. Create the tables as a migration file in `sites/<name>/supabase/migrations/`, apply it,
   and turn on RLS with policies in the same migration.
3. Put the project's address and anon key in the site, and anything secret in Vercel's
   environment settings.
4. Test it for real: add a row through the page, read it back, then check that a visitor
   cannot read or change what they should not.

## 4. Put it online

```bash
cd sites/<name>
vercel link --yes        # the first time: makes the Vercel project
vercel --prod --yes
```

Read the address Vercel prints, open it in Chrome, and check the page loads and works
(submit a test entry if it has a form, then remove it). Then give the person the link.

## 5. Tell them what it costs

Say this once, the first time they publish, in two sentences:

- Vercel's free plan (Hobby) is for personal, non-commercial sites. A site for a business
  belongs on Vercel Pro, about $20 a month per person: they can upgrade at vercel.com,
  under Settings, then Billing.
- Supabase's free plan allows business use, with two projects, and a project pauses after
  a week with no visits (one click in Supabase wakes it). Supabase Pro is about $25 a month.

## 6. Write it down

Add the site to `state/current.md` under a "Sites" heading: its name, link, folder,
whether it has a database, and today's date. Later updates go in the same place.
