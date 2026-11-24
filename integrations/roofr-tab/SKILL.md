---
name: connect-crm
description: "Look things up in Roofr (jobs, sales, customers, appointments) through the person's own signed-in Roofr tab. Use whenever a question needs anything from Roofr."
---

# Roofr: read it through their own Roofr tab

Roofr has no API key that a customer can make, and you never need one. Roofr's website runs on its
own web endpoints. You call those same endpoints from {{USER}}'s Roofr tab, where they are already
signed in, so they see only what their own Roofr account can see. There is no key, endpoint or
credential to ask for, and none is missing.

## Which browser

{{CHROME}}

## How

1. Find their Roofr tab, or open `https://app.roofr.com`. If it shows a sign-in page, have them sign
   in themselves. Never type or ask for their password.
2. Read the team number from the address: `https://app.roofr.com/dashboard/team/<team>/...`. If the
   address has no team number, open Roofr's dashboard first so it does.
3. In that tab, make same-origin requests with the browser's page-script tool (Claude in Chrome's
   JavaScript tool, or ChatGPT's if `@Chrome` can run one):

   ```js
   const team = (location.pathname.match(/team\/(\d+)/) || [])[1];  // missing: open the dashboard first
   const get = (path) => fetch(path, { headers: { 'team-id': team, Accept: 'application/json',
     'x-requested-with': 'XMLHttpRequest' } }).then((r) => (r.ok ? r.json() : Promise.reject(r.status)));
   ```

   Return only what answers the question (counts, totals, a few rows), never pages of raw data.

   If a script that uses `fetch` comes back `undefined` or empty, the browser tool ran it but did not
   wait for the answer (ChatGPT's Chrome tool can work this way). Use a request that answers at once:

   ```js
   const team = (location.pathname.match(/team\/(\d+)/) || [])[1];
   const x = new XMLHttpRequest();
   x.open('GET', '/api/jobs?per_page=25&filter[q]=smith', false);  // false = wait for the answer
   x.setRequestHeader('team-id', team);
   x.setRequestHeader('Accept', 'application/json');
   x.send();
   x.status === 200 ? x.responseText.slice(0, 20000) : 'status ' + x.status;
   ```

   Change only the address. If that also comes back empty, start the request in one step
   (`fetch(...).then((r) => r.json()).then((d) => { window.__roofr = d; })`) and read
   `JSON.stringify(window.__roofr)` in a second step a moment later.
4. If the browser tool cannot run page scripts at all, read the same things from the website itself:
   the jobs list with its filters, a job card, the calendar and the reports. Say that you read them from
   the screen.

## Endpoints (read only)

| What | Request |
|------|---------|
| Search jobs by name, phone, address or job number | `/api/jobs?per_page=25&filter[q]=<text>` |
| All jobs, page by page | `/api/jobs?per_page=100&page=<n>`. Each row has `stage`, `value` and `close_date`. Follow `links.next` until it is empty; ignore `meta.last_page`. Of the filters, only `filter[q]` and `filter[job_workflow_id]=<id>` work on this list; others are silently ignored. |
| One job in full: stage, value, sold date (`close_date`), insurance, assignees, tags, the Lost or Won reason (`resolution`) | `/api/job/<id>` (singular `job`) |
| Everyone on a job | `/api/job/<id>/contacts` |
| A job's history: stage changes, notes | `/api/job/<id>/activities` |
| Find a customer by phone or name | `/api/contacts?search=<text>&include[]=latestJobContact&include[]=jobContactsCount` |
| Appointments in a time range | `/api/calendar/event?timezone=<time zone, e.g. America/Phoenix>&start_date_time=YYYY-MM-DD HH:MM:SS&end_date_time=YYYY-MM-DD HH:MM:SS` (all three are required) |
| Workflows and their stages | `/api/job-workflows` |

**Sales for a period.** A sold job carries its sold date in `close_date` on `/api/job/<id>`. Find this
company's won stages in `/api/job-workflows` (for example "Proposal signed" or "Insurance job won"),
page through `/api/jobs` (each row carries `stage`, `value` and `close_date`), and count the jobs in those
stages whose `close_date` falls inside the period, adding up `value` for the total. Say which stages you
counted. A `close_date` with a time is in UTC: convert it to their time zone before deciding the day.
A bare day (YYYY-MM-DD) is already the day: use it as it is.

## Rules

- Read only. Never send a request that changes anything (PUT, POST, PATCH or DELETE). For a change,
  do it in the website, and only after they ask and confirm. Never get around a security check or a CAPTCHA.
- Be gentle: one request at a time, a short pause between pages, and stop once the question is answered.
- A 401 or 419 answer means they are signed out: ask them to sign in again in that tab, then try once more.
- Never copy, save, print or send their cookies, session or any token from the page, and never use them
  outside that tab.
- Never send them to an outside automation or integration service.
- Never ask for another person's setup, tools, endpoints, accounts or credentials, and never decide something
  is missing because `.env` has no Roofr entry: there is none, by design. If the scripts do not work, read
  the Roofr pages instead.
