---
name: phone-ctm
description: Look up the business's phone calls in CallTrackingMetrics, read-only. Use when the person asks who called, when a customer last called, what a customer said on a call, how many calls came in on a day, which calls were missed, what calls a teammate took, or wants the recording of a call.
---

# Phone calls (CallTrackingMetrics, read-only)

Call history from CallTrackingMetrics, through the business's data bridge: address
`TM_BRIDGE_URL`, header `Authorization: Bearer <TM_BRIDGE_TOKEN>`, both from `.env`.
Never print the token.

You can look calls up. You cannot change anything in the phone system, place a call,
or send a text. If the person wants one of those, they do it themselves in CallTrackingMetrics.

## Endpoints (add each to the bridge address)

| Endpoint | Use |
|---|---|
| `/calls` | A list of calls, newest first |
| `/call/<id>` | One call, with its transcript and summary when there is one |

### `/calls` filters

| Filter | Meaning |
|---|---|
| `phone` | A customer's number, any format, all 10 digits. Matches calls to or from it. |
| `from`, `to` | Local calendar days, `YYYY-MM-DD`. `to` includes that whole day. |
| `agent` | Part of a teammate's name |
| `direction` | `inbound` or `outbound` |
| `status` | `answered`, `no answer`, `busy`, `hangup` |
| `limit`, `offset` | Up to 200 a page. Follow `next_offset` until it is null. |

You must give a phone number, a `from` date, or both.

### What comes back

`called_at` (UTC), `direction`, `status`, `duration_seconds`, `caller_number`,
`called_number`, `caller_name`, `caller_city`, `caller_state`, `agent` (who took it),
`tracking_source` and `tracking_label` (which number or ad the call came through),
`is_ivr` (handled by the phone menu, not a person), and `recording`.

## Rules

- **Times are UTC in the data.** Convert to the local time zone in `CLAUDE.md` before
  you tell the person a time.
- **`recording` is a link, not audio.** It opens in CallTrackingMetrics and needs their
  own sign-in. Give them the link. You cannot listen to it.
- **Transcripts are not always there.** They are written a while after the call, and
  not for every call. If `/call/<id>` has no transcript, say so and offer the recording
  link. Never guess what was said.
- **A transcript is a machine's hearing of a call.** Names, addresses and numbers in it
  are often wrong. Say "the transcript says" and check details against the CRM before
  anyone relies on them.
- **There are no outcome tags here.** Do not say a call "booked" or "did not book" from
  call data alone. Check the CRM.
- **For "how many" questions over a long stretch,** page through with a date range and
  count. Say the date range in your answer.
- **These are customers' conversations.** Use them for the work in front of the person.
  Do not paste a transcript into a message to anyone outside the company.

## Example

"When did 555-555-0142 last call, and what did they want?"

1. `GET /calls?phone=5555550142&limit=5`
2. Take the newest answered call's `id`, then `GET /call/<id>`.
3. Answer with the local date and time, who took it, and a two-line summary of the
   transcript. Add the recording link. If there is no transcript, say that.
