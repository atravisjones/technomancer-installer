---
name: the-boys
description: "Protocol reference for MARVIN's multi-agent swarm. NOT a standalone agent — MARVIN executes this protocol directly. Gemini (agy-call.sh / Antigravity OAuth) + Codex workers (free), optional Sonnet worker (window-costly), Gemini reviewer, Claude PM."
model: inherit
color: blue
---

# The Boys — Multi-AI Swarm Protocol

This is a **protocol that MARVIN executes directly** — not a standalone agent. When the user says "the boys" or a task is non-trivial, MARVIN follows this protocol in the main session.

**The core idea:** your Claude usage window is the scarce, expensive resource. Gemini (via Antigravity OAuth) and Codex (via a ChatGPT account) are free at the margin. So Claude acts as the PM — orchestrating, deciding, applying — while free CLI workers do the exploration, research, and drafting.

**Prerequisites:** see `docs/the-boys-setup.md` — you need the `codex` CLI and the Antigravity (`agy`) CLI installed and authenticated before this protocol works.

---

## HARD RULES

1. **Workers NEVER apply code changes.** They research, diagnose, and propose only. Every worker prompt must explicitly say: "Propose changes, do not apply them."
2. **Approval checkpoint is MANDATORY.** After the reviewer synthesizes, the PM presents findings to the user. NO code is applied until the user approves.
3. **Gemini is the reviewer/synthesizer.** After all workers finish, a fresh Gemini instance (via `agy-call.sh`) reviews all outputs and synthesizes a summary for the PM. FREE.
4. **Token economics: the Claude usage window is the scarce resource.** Gemini and Codex are free and unconstrained — fan out freely. A Sonnet worker and the Claude PM share the user's Claude plan window — use Sonnet sparingly and keep the PM lean.
5. **No Haiku.** Only Gemini, Codex, and (sometimes) Sonnet.
6. **Minimum swarm: 3 Gemini + 2 Codex = 5 workers.** Sonnet is OPTIONAL — add only when the task genuinely needs Anthropic-style judgment free models can't match. **Cap concurrent Gemini (agy) at ~3** — agy contends under load; for wider fan-outs add Codex, not more agy.
7. **ALL workers dispatched in ONE message.** Multiple tool calls in a single response. Never one at a time across turns.
8. **All agents run in background.** (`run_in_background: true` for Bash, or background Agent calls)
9. **The PM does ONLY:** orchestrate, present recommendations, make final decisions, apply approved code.
10. **The PM does NOT:** explore, research, implement, or read raw agent dumps directly.
11. **Track the work.** Create a task/todo entry per independent work unit before dispatching.
12. **Wait for ALL results before acting.** No early starts, no partial applications.
13. **Codex model = config default, tiered by task.** Bare `codex exec` uses `~/.codex/config.toml`. Tiers available vary by ChatGPT account — verify which work on yours (the codex startup banner `model: …` is the only source of truth; models self-report their family name regardless of tier).

---

## The Team

| Role | Model | Dispatch | Window Cost | Strengths |
|------|-------|----------|-------------|-----------|
| **PM** | Claude (MARVIN — your main session) | Direct — you | Consumes window — stay lean | Hardest-problem coder, long-horizon orchestration, best "taste" for synthesis, devil's advocate |
| **Gemini worker** (3-5) | `agy-call.sh` (Antigravity OAuth; model via `AGY_MODEL`) | `Bash` bg | FREE | Long-context, alternative framings, fast turnaround, large-codebase digestion |
| **Codex worker** (2-5) | `codex exec` (config default) | `Bash` bg | FREE (ChatGPT plan) | Tool-using investigator, strong coding, browse/MCP/evidence gathering, polished copy |
| **Sonnet worker** (0-1, optional) | Sonnet | `Agent` tool `model: "sonnet"` bg | Consumes window | Anthropic-style judgment — nuanced PR review, writing polish, subtle security analysis. Add ONLY when free models can't match. |
| **Gemini Reviewer** (1) | `agy-call.sh` | `Bash` bg | FREE | Synthesizes all worker outputs. Always a fresh instance — never reviews its own work. |

### Agent Counts

| Task Complexity | Gemini | Codex | Sonnet | Reviewer | Total |
|-----------------|--------|-------|--------|----------|-------|
| Small fix / quick research | 3 | 2 | 0 | 1 | 6 |
| Medium feature / review | 3-4 | 3 | 0-1 | 1 | 7-9 |
| Large refactor / architecture | 4-5 | 4-5 | 0-1 | 1 | 9-12 |

Default to Sonnet = 0. Bump to 1 only when the task genuinely demands Anthropic-style judgment.

---

## Convergent vs Divergent Patterns

**This is THE core decision for every swarm.** Pick one pattern per invocation.

### Convergent (DEFAULT for research, design, debugging, architecture)

All workers tackle **the same problem**, but from **different framings / roles**. The point is not to run identical prompts — it's to exploit each model's distinct way of thinking.

**Role-based prompts:**
- **Gemini:** *"What's a totally different way to frame this problem? What alternative approach are we missing?"* (orthogonal reasoner, large context)
- **Codex:** *"What do the docs, tools, and evidence actually say? Browse, verify, gather proof."* (tool-using investigator)
- **Sonnet** (if included): *"Critique the current approach. What are the hidden risks, failure modes, and edge cases?"* (skeptical Anthropic voice)
- **PM (you, during review):** *"What are we still missing? What would a stubborn senior engineer push back on?"*

Use when: architecture decisions, tricky debugging, "how should we build X", security reviews, product/UX direction.

### Divergent (ONLY for mechanical fan-out)

Split a large known task across workers — each gets a different piece. No one worker needs the whole picture.

Use when: refactoring N files with the same pattern, writing tests for multiple functions, mechanical renames, bulk extraction. Only when the approach is already decided and the work is obviously parallelizable.

### When in doubt → convergent

The convergent pattern is better for ~80% of tasks. If the work could be described as "figure out X" or "should we do Y" or "why is Z broken" → convergent. If it's "apply this known change to these 15 files" → divergent.

---

## Diversification Principle

**Same problem, different model brains = better coverage.** Never put 2 of the same model on the same exact scope — that's wasted compute for near-identical output.

Different models have different blind spots:
- **Gemini** — fast, long-context, search-grounded; style is concise and orthogonal
- **Codex** — tool/evidence-heavy, strong agentic workflows, polished copy
- **Sonnet** — Anthropic taste, frontend/design judgment, nuanced security instincts
- **Claude PM** — the deepest critic and synthesizer

Mix them to catch what any single model would miss.

---

## Routing Rules

| Work Type | Pattern | Route To |
|-----------|---------|----------|
| Architecture / design decision | Convergent | Gemini (reframe) + Codex (evidence) + optional Sonnet (critique) |
| Tricky bug hunt | Convergent | Gemini (alt hypotheses) + Codex (reproduce/test) + optional Sonnet (edge cases) |
| Code review / security audit | Convergent | Gemini + Codex + optional Sonnet, all on same scope, different lenses |
| Long-document / large-codebase analysis | Convergent | Gemini leads (long context), Codex cross-checks |
| Research / exploration | Convergent | Gemini + Codex with different framings |
| Mechanical refactor across N files | Divergent | Split by file/module, mix models per chunk |
| Implementation of an approved plan | Divergent | Split scope, PM applies or workers propose diffs |
| Synthesizing all worker outputs | — | Gemini Reviewer (fresh instance) |
| Approval checkpoint | — | PM presents to the user |

---

## Mandatory Sequence

```
Step 1: Track the work (todo/task entry per independent work unit)
Step 2: Pick convergent or divergent. Write role-based prompts (convergent) or scope-split prompts (divergent).
Step 3: Dispatch ALL workers in ONE message (background)
         — Every prompt MUST include: "Propose changes, do not apply them."
Step 4: Wait for ALL workers to complete
Step 5: Dispatch Gemini Reviewer — pass all worker outputs, get synthesis (background)
Step 6: Read the Gemini Reviewer's summary (the PM does NOT read raw agent output)
Step 7: APPROVAL CHECKPOINT — Present findings to the user, scaled to risk:
         — Small fix → one-liner recommendation
         — Multi-file change → full breakdown with proposed diffs
         — Wait for the user to approve, adjust, or reject
Step 8: Apply approved code — the PM decides how:
         — Small change → PM applies directly
         — Multi-file change → dispatch workers with "implement this approved plan" instructions
Step 9: Report to the user
```

**Step 7 is NON-NEGOTIABLE — no code lands without the user's approval.**

---

## Dispatch Commands

### Gemini (via agy-call.sh / Antigravity OAuth) — FREE
```bash
bash tools/agy-call.sh "$(cat <<'PROMPT'
[role-based framing + full context/file contents + "Propose changes, do not apply them."]
PROMPT
)" 2>/dev/null
```
- Always `run_in_background: true`
- Always `2>/dev/null` to suppress agy launch/log chatter
- Runs Antigravity (`agy`) over OAuth, then extracts the reply from agy's SQLite conversation DB (`agy -p` print mode is broken — it runs the model but never prints to stdout). Reply text comes back clean on stdout.
- **Cap concurrent agy calls at ~3.** Concurrency is *safe* (no conversation cross-contamination) but **slow under load** — 5 parallel calls drag each to ~70s and raise retry rates. For wide fan-outs keep agy ≤3 and put the extra breadth on Codex (no contention).
- Latency is variable (~10-25s solo; ~70s+ under concurrency; occasional hang → hard-killed at `AGY_HARD_TIMEOUT`, default 180s, still recovers a completed reply from the DB)
- Set model with `AGY_MODEL` env; default is agy's active model
- Logs successes/failures to `tools/boys-failures.log`
- **Must include file contents in prompt** — external agents can't read your session context
- For larger prompts, use `--prompt-file <path>`: `bash tools/agy-call.sh --prompt-file /path/to/prompt.md`

### Codex — FREE
```bash
echo "" | codex exec "[role-based framing + full context + propose-only]"
```
- Always `run_in_background: true`
- Always pipe empty stdin (`echo "" |`) — otherwise codex hangs on "Reading additional input from stdin"
- **Model:** default is the config value (`~/.codex/config.toml`); add `-m <model>` only for deliberate tier changes. Verify which tiers your ChatGPT account can access — the startup banner is the only source of truth.
- **Must include file contents in prompt** (codex can also read files itself when run from the repo root)
- **Windows sandbox gotcha:** Codex's workspace-write sandbox CHOKES on paths with spaces or parens. Symptom: "windows sandbox: spawn setup refresh" before any file read. Either copy/symlink to a clean path first OR run from a clean repo root and pass quoted absolute paths inside the prompt.
- **From Python:** direct `subprocess` invocation of codex can die with rollout-recording errors on Windows — shell out via Git Bash instead: `["C:\\Program Files\\Git\\bin\\bash.exe", "-c", "echo '' | codex exec …"]`

### Sonnet (optional) — CONSUMES CLAUDE WINDOW
```
Agent tool:
  subagent_type: "general-purpose"
  model: "sonnet"
  prompt: "[focused, bounded task with full context + propose-only]"
  run_in_background: true
```
- Default: NOT dispatched. Add only when needed.
- Keep the task tightly scoped — every Sonnet call eats the same window the PM needs to keep running.

### Gemini Reviewer — FREE
```bash
bash tools/agy-call.sh "$(cat <<'PROMPT'
You are the synthesis reviewer. Below are outputs from multiple AI workers on the same problem,
each prompted with a different framing/role. Identify the strongest ideas, flag conflicts,
deduplicate, and give a concise summary ranked by priority.

[paste all worker outputs here, tagged by agent ID and role]
PROMPT
)" 2>/dev/null
```
- Dispatched AFTER all workers complete
- Fresh instance — never reviews its own worker output
- Returns the only thing the PM reads

### The PM (your main Claude session — MARVIN)
- **Allowed:** orchestrate, read the Gemini reviewer's synthesis, make final decisions, apply code (Edit/Write)
- **NOT allowed:** explore, research, implement in advance, read raw agent output directly
- **Window discipline:** every context dump and tool call the PM makes is a tax on the same window a Sonnet worker shares. Stay lean.

---

## Dispatch Rules

1. **ALL workers in ONE message** — true parallel
2. **Always run in background**
3. **Convergent by default** — different framings on the same problem, not the same prompt on every model
4. **Include file contents in prompts** — external agents can't read your session context
5. **Suppress stderr on Gemini** (`2>/dev/null` — the wrapper logs to a file, you don't need the retry chatter inline)
6. **Collect ALL outputs before acting**
7. **Tag each worker's output** in your report (Gemini-reframe, Codex-evidence, Sonnet-critique, etc.)
8. **Minimum: 3 Gemini + 2 Codex.** Sonnet optional.
9. **Gemini reviewer is always a fresh instance** — never reviews its own work
10. **Never pin Codex to a specific model version in dispatch commands.** Update the config, not the call site.

---

## Failure Modes & Recovery

### Gemini (agy) failure
**Symptom:** `agy-call.sh` logs `FAILED` — `no_conversation_id` (auth/launch broke), `db_missing`, or `extract_empty` (agy changed its DB format).

**Action:**
1. Wrapper already logged to `tools/boys-failures.log`
2. `extract_empty` → agy likely changed its on-disk format; fix `tools/agy-extract.py` (`step_type=15` = model response), dispatch a Codex diagnostic per CLI Failure Handling
3. `no_conversation_id` → re-check OAuth (`agy models` should list models); if auth is broken, re-dispatch the slot to Codex and proceed with a degraded swarm
4. If the reviewer Gemini also fails, the PM synthesizes directly from Codex outputs

### Codex sandbox bail
**Symptom:** Codex output contains "windows sandbox: spawn setup refresh" before any file activity. Exit 0 but no real work done.

**Cause:** Workdir path has spaces or parens — the sandbox wrapper can't build a valid container.

**Action:**
1. DON'T retry the same path — it'll fail identically
2. Restart codex from a clean path (your MARVIN repo root is always safe)
3. Pass the messy-path target as a quoted absolute path inside the prompt body

### Codex stdin hang
**Symptom:** `codex exec "..."` runs forever, no output.

**Cause:** Codex thinks stdin is still open.

**Action:** Prefix the call with `echo "" |` — `echo "" | codex exec "prompt"`. Closes stdin immediately.

### Agy print mode (handled by the wrapper)
`agy -p` print mode is broken — it authenticates, runs the model, completes the stream, but never prints to stdout. `tools/agy-call.sh` works around this by extracting the reply from agy's SQLite conversation DB (`tools/agy-extract.py`). Always call `agy-call.sh`, never raw `agy -p` (you'd get empty output).

**Telemetry:** Scan `tools/boys-failures.log` before dispatching — patterns surface there.

---

## Anti-Patterns (MUST NOT do)

- **Workers applying code changes** — propose only, never edit/write files
- **Skipping the approval checkpoint** — the user must approve before any code lands
- **Identical prompts on every model** — that's not convergent, that's waste. Always use role-based framings.
- **Defaulting to Sonnet** — Sonnet is optional and window-costly. Use Gemini + Codex first.
- **The PM exploring/researching** — delegate to workers
- **Dispatching one agent at a time** — always batch in one message
- **Fewer than 5 total workers** on non-trivial tasks (3 Gemini + 2 Codex floor)
- **The PM reading raw agent dumps** — always go through the Gemini reviewer first
- **Homogeneous grouping** — never put 2 of the same model on the same exact scope
- **Gemini reviewer reviewing its own output** — always a separate instance
- **Worker prompts missing "propose only"** — every prompt must say it explicitly
- **Pinning Codex to a specific model in dispatch** — use bare `codex exec`, change the config to upgrade
- **Faking a CLI worker via the Agent tool** — the Agent tool only spawns Claude subagents; naming one "codex-1" creates a Claude model wearing a nametag, burning your paid window while pretending to be free
- **Calling raw `agy -p`** — print mode is broken (empty stdout). Always go through `agy-call.sh`.

---

## PM Review Checklist

When reviewing the Gemini reviewer's synthesis before presenting to the user:
- [ ] Did workers disagree? If so, surface the disagreement honestly.
- [ ] Does the recommended approach match existing style/conventions?
- [ ] Security issues flagged?
- [ ] Is the simplest correct solution being used?
- [ ] Unnecessary additions to prune?
- [ ] Would the user approve this change?

---

## Example: Convergent Swarm (architecture decision)

**User:** "Should we migrate the dashboard to realtime subscriptions or keep polling?"

**MARVIN thinks:** Architecture decision → convergent. Different framings on the same question.

**Step 1:** Track the work units.

**Step 2 — dispatch workers in ONE message, role-based framings:**

- **Gemini-reframe:** "Reframe this problem from first principles. What are the 3 least obvious alternative architectures? Is there a hybrid nobody's considered?"
- **Gemini-context:** "Read the entire dashboard codebase + current polling implementation (files inlined below). What does the existing code tell us about which approach fits better?"
- **Codex-evidence:** "Research the realtime service's limits, cost model, and known gotchas at our scale. Cite official docs. What's the real-world operational burden vs polling?"
- **Codex-prototype:** "Sketch a minimum migration path. What's the smallest PR that proves realtime works end-to-end? What breaks?"
- *(Sonnet skipped — no Anthropic-style judgment uniquely needed here)*

**Step 3:** Wait for all 4 to complete.

**Step 4:** Dispatch the Gemini Reviewer (fresh instance) with all 4 outputs. Synthesis highlights: the two strongest approaches, where workers disagreed, recommended decision, risks.

**Step 5:** Present to the user — the call, the tradeoff, the dissenting view.

**Step 6:** The user decides → execute.

---

## Example: Divergent Swarm (mechanical refactor)

**User:** "Rename `job_close_date` to `close_date` everywhere."

**MARVIN thinks:** Mechanical, known approach → divergent. Split by directory.

- Gemini-1: `services/sync/` files
- Gemini-2: `services/search/` files
- Gemini-3: `services/api/` files
- Codex-1: `dashboard/` files
- Codex-2: grep the whole repo for stragglers

All propose diffs only → Gemini Reviewer dedupes + flags conflicts → the user approves → the PM applies.

---

## Key Constraints

- **Never auto-commit or push** — the user or the PM handles git
- **Never modify .env** or expose secrets in agent prompts
- **Always use `tools/agy-call.sh`** for the Gemini-class worker — never call `agy` directly (skips DB extraction + the failure log)
- **Codex route:** `echo "" | codex exec` with NO model flag (config default; pipe empty stdin to avoid the stdin hang)
- **If an agent fails or returns garbage**, note it and move on — don't block the swarm
- **Present conflicts honestly** — if workers disagree, show all positions with the recommendation
- **Proactive dispatch** — spin up the boys automatically for non-trivial tasks
- **Window discipline:** every Sonnet call and every PM tool call is a tax on the same Claude plan window. Favor Gemini and Codex. Keep the PM's context lean — read the reviewer's summary, not every raw dump.
