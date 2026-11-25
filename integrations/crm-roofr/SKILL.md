---
name: crm-roofr
description: Read the business's Roofr job pipeline (jobs, stages, lead sources, values, owners). Use for any question about jobs, leads, sales, close rates, revenue or the pipeline, such as "how many jobs did we win last month", "what is our close rate by lead source", or "export this week's jobs".
---

# Roofr jobs (read-only)

Read-only access to the business's Roofr pipeline, through its data bridge. The bridge's
address is `TM_BRIDGE_URL` and its token is `TM_BRIDGE_TOKEN`, both in the workspace `.env`.

Use this first, with no browser: do not open Chrome or Roofr's website for anything it answers.
It carries jobs, stages, values, owners, lead sources and sold dates. For what it does not carry
(notes, a job's history, contacts, appointments), or when it answers with an error, use the
`connect-crm` skill, which reads the person's own signed-in Roofr tab, and say that you switched.

## Auth

Every request except `/health` needs the header `Authorization: Bearer <token>`.

- Never print the token, log it, or put it in a reply or a file other than `.env`.
- Read it inside the command so it never shows on screen (see the examples).
- If `.env` has no token, say Roofr is not connected yet. Do not guess one.

## Endpoints (add each to the bridge address)

| Endpoint | Use |
|----------|-----|
| `/health` | Liveness check, no auth |
| `/schema` | Column reference and endpoint list. Call this when unsure of a field. |
| `/summary` | Totals, close rates, and breakdowns by category, workflow, owner and lead source |
| `/jobs` | Paginated job list. Filters: `from`, `to`, `closed_from`, `closed_to` (YYYY-MM-DD), `stage`, `stage_category`, `workflow`, `owner`. `format=json` or `csv`. Max 1000 rows a page. |
| `/job/<id>` | One job by its Roofr ID |

## Which one to call

1. **Counts, totals, averages, breakdowns: call `/summary` first.** It is one fast request.
2. Call `/jobs` only when row-level detail is needed.
3. For a spreadsheet, use `/jobs?format=csv` with a tight date range.
4. Page with `next_offset` until it is null.
5. Never loop `/job/<id>` over many jobs. Use `/jobs` with filters.

## Two kinds of date

- `from` and `to` go by the day a job was **created**. Use them for leads and new jobs.
- `closed_from` and `closed_to` go by the day a job **closed**, in the business's local
  time. Use them for sales: "what did we sell today" is
  `/jobs?stage_category=won&closed_from=<today>&closed_to=<today>`, and `/summary` takes
  the same two for totals. A job is usually sold days or months after it was created, so
  `from`/`to` give the wrong answer to a sales question.
- Report retail and insurance work separately (`workflow`) when both exist. An insurance
  job reaching a won stage is often an old claim moving forward, not a fresh sale.
- Check the answer: every row's `close_date` must fall in the days you asked for. If it
  does not, the filter was not applied; say so, do not report the rows as that day's sales.
- The data is a copy of Roofr that refreshes every few minutes, so a sale from the last
  few minutes may be missing.

## Limits

- 60 seconds a request, 1000 rows a page.
- More than 10,000 rows: split the request by month.
- Dates are `YYYY-MM-DD`.
- `stage_category` values are lowercase: `won`, `lost`, `in_progress`, `unqualified`, `rescheduling`.

## Examples

Mac, or Git Bash on Windows:

```bash
URL=$(grep '^TM_BRIDGE_URL=' .env | cut -d= -f2-)
TOKEN=$(grep '^TM_BRIDGE_TOKEN=' .env | cut -d= -f2-)
curl -s -H "Authorization: Bearer $TOKEN" "$URL/summary?from=2026-01-01&to=2026-01-31"
```

PowerShell:

```powershell
$env_ = Get-Content .env
$url = ($env_ -match '^TM_BRIDGE_URL=')[0] -replace '^TM_BRIDGE_URL=', ''
$token = ($env_ -match '^TM_BRIDGE_TOKEN=')[0] -replace '^TM_BRIDGE_TOKEN=', ''
Invoke-RestMethod "$url/summary?from=2026-01-01&to=2026-01-31" -Headers @{ Authorization = "Bearer $token" }
```

When reporting numbers, say the date range they cover.
