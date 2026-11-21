#!/bin/bash
# Antigravity CLI wrapper for the boys swarm — OAuth path, extract-from-DB.
# Usage: ./agy-call.sh "your prompt here" [extra args...]
#    or: ./agy-call.sh --prompt-file <path> [extra args...]
#
# WHY THIS EXISTS (2026-06-25): Google killed the gemini CLI's free OAuth tier
# (IneligibleTierError / UNSUPPORTED_CLIENT) and forces migration to Antigravity.
# Antigravity's OAuth auth WORKS (any Google account), BUT `agy -p`
# print mode is broken — it authenticates, runs the model, completes the stream,
# yet never writes the reply to stdout. The reply IS persisted to a per-conversation
# SQLite DB. So we run agy headlessly, capture the conversation id from its log,
# and extract the model text from the DB via tools/agy-extract.py.
#
# FRAGILITY: extraction reverse-engineers agy's protobuf-in-SQLite format
# (changed .pb -> .db in agy 1.0.12). If agy changes the format again, update
# tools/agy-extract.py (step_type=15 = model response).
#
# Env knobs:
#   AGY_PRINT_TIMEOUT  agy's internal print wait (default 120s; agy format e.g. 5m)
#   AGY_HARD_TIMEOUT   outer wall-clock kill in seconds (default 180)
#   AGY_RETRIES        attempts before giving up (default 3; agy's print persistence
#                      is flaky ~1-in-N — a fresh attempt almost always lands)
#   AGY_MODEL          pass-through --model (e.g. "Gemini 3.5 Flash (High)")

PROMPT_FILE=""
if [ "$1" = "--prompt-file" ] || [ "$1" = "-f" ]; then
  PROMPT_FILE="$2"
  shift 2
  if [ ! -f "$PROMPT_FILE" ]; then
    echo "prompt file not found: $PROMPT_FILE" >&2
    exit 1
  fi
  PROMPT="$(cat "$PROMPT_FILE")"
else
  PROMPT="$1"
  shift
fi
EXTRA_ARGS="$@"

if [ -z "$PROMPT" ]; then
  echo "Usage: agy-call.sh \"prompt\" [extra args...]" >&2
  echo "   or: agy-call.sh --prompt-file <path> [extra args...]" >&2
  exit 1
fi

PRINT_TIMEOUT="${AGY_PRINT_TIMEOUT:-120s}"
HARD_TIMEOUT="${AGY_HARD_TIMEOUT:-180}"
# agy's print-mode persistence is flaky: ~1 in N runs exits 0 but never writes
# the model-response step to the conversation DB (incomplete step set). The
# failure is intermittent — a fresh attempt almost always lands. So retry.
RETRIES="${AGY_RETRIES:-3}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_FILE="${SCRIPT_DIR}/boys-failures.log"
EXTRACT="${SCRIPT_DIR}/agy-extract.py"
CONV_DIR="${HOME}/.gemini/antigravity-cli/conversations"

MODEL_ARG=()
[ -n "$AGY_MODEL" ] && MODEL_ARG=(--model "$AGY_MODEL")

LAST_REASON="no_attempt"
LAST_CONV=""

for attempt in $(seq 1 "$RETRIES"); do
  TS="$(date +%Y-%m-%dT%H:%M:%S%z)"
  AGYLOG="$(mktemp -t agy-call.XXXXXX.log)"

  # Run agy headlessly. stdout is empty (broken print mode) — we discard it and
  # recover the reply from the conversation DB. Hard outer timeout guards hangs.
  timeout "$HARD_TIMEOUT" agy -p "$PROMPT" \
    --dangerously-skip-permissions \
    --print-timeout "$PRINT_TIMEOUT" \
    --log-file "$AGYLOG" \
    "${MODEL_ARG[@]}" $EXTRA_ARGS >/dev/null 2>&1
  AGY_EXIT=$?

  CONV_ID="$(grep -oE 'conversation=[0-9a-f-]{36}' "$AGYLOG" 2>/dev/null | head -1 | cut -d= -f2)"
  STREAM_DONE="$(grep -c 'Stream completed' "$AGYLOG" 2>/dev/null)"
  rm -f "$AGYLOG"

  if [ -z "$CONV_ID" ]; then
    LAST_REASON="no_conversation_id"; LAST_CONV=""
    echo ">>> attempt ${attempt}/${RETRIES}: agy produced no conversation (auth/launch?). agy_exit=${AGY_EXIT}" >&2
    continue
  fi
  LAST_CONV="$CONV_ID"
  DB="${CONV_DIR}/${CONV_ID}.db"
  if [ ! -f "$DB" ]; then
    LAST_REASON="db_missing"
    echo ">>> attempt ${attempt}/${RETRIES}: conversation DB missing ($CONV_ID)" >&2
    continue
  fi

  OUTPUT="$(python "$EXTRACT" "$DB" 2>/dev/null)"
  if [ $? -eq 0 ] && [ -n "$OUTPUT" ]; then
    echo "${TS} | agy-call | SUCCESS | conv=${CONV_ID} | agy_exit=${AGY_EXIT} | stream_done=${STREAM_DONE} | attempt=${attempt}" >> "$LOG_FILE"
    printf '%s\n' "$OUTPUT"
    exit 0
  fi

  LAST_REASON="extract_empty"
  echo ">>> attempt ${attempt}/${RETRIES}: agy exited 0 but no reply persisted (conv=${CONV_ID}); retrying" >&2
done

TS="$(date +%Y-%m-%dT%H:%M:%S%z)"
echo "${TS} | agy-call | FAILED | ${LAST_REASON} | conv=${LAST_CONV} | retries=${RETRIES}" >> "$LOG_FILE"
echo ">>> agy reply could not be extracted after ${RETRIES} attempts (last: ${LAST_REASON}). If extract_empty persists, agy may have changed its DB format — check tools/agy-extract.py" >&2
exit 1
