#!/usr/bin/env python3
"""Extract the model's reply from an Antigravity (agy) conversation .db.

Antigravity CLI's print mode (`agy -p`) is broken on Windows — it authenticates,
runs the model, and completes the stream, but never writes the response to stdout.
The response IS persisted to a per-conversation SQLite DB at
  ~/.gemini/antigravity-cli/conversations/<conversation-id>.db
inside protobuf-encoded BLOBs. This script pulls the assistant text back out.

Usage:  python tools/agy-extract.py <path-to-conversation.db>
Prints the response to stdout, exit 0 on success; prints nothing, exit 1 on miss.

Schema (agy 1.0.12, format may change on agy updates — this is reverse-engineered):
  table `steps`(idx, step_type, step_payload BLOB, ...)
    step_type=14 -> user message
    step_type=15 -> model response   (what we want; pure response, no prompt echo)
    step_type=23 -> turn summary      (mixes prompt + response; fallback only)
  step_payload is raw protobuf wire format with no known .proto, so we do a
  generic wire-format walk and keep the length-delimited fields that look like
  natural-language text, dropping id-like noise (UUIDs, bot-ids, session ids).
"""
import sqlite3
import sys
import re

UUID_RE = re.compile(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}', re.I)
# base64url-ish opaque ids (response ids / trace ids), e.g. 'YFE9avncDvHmz7IPqOKMmAk'
B64ID_RE = re.compile(r'^[A-Za-z0-9_-]{16,40}$')
HEXID_RE = re.compile(r'^[0-9a-f]{16,}$', re.I)
INTID_RE = re.compile(r'^-?\d{6,}$')          # session id values like -3750763034362895579
NOISE_EXACT = {'sessionID', 'session_id', 'main', 'user', 'model', 'assistant'}


def read_varint(b, i, n):
    """Correct protobuf varint: continuation is the LAST byte's high bit."""
    shift = 0
    result = 0
    while i < n:
        byte = b[i]
        i += 1
        result |= (byte & 0x7F) << shift
        if not (byte & 0x80):
            return result, i
        shift += 7
        if shift > 70:          # runaway guard
            break
    return result, i


def is_texty(s):
    """True if the string reads as natural-language text (not binary noise).

    Rejects any embedded control byte other than \\n \\t \\r — protobuf framing
    strings (e.g. the trajectory-id pair joined by \\x10\\x02) carry such bytes
    and would otherwise pass a simple printable-ratio test.
    """
    if not s:
        return False
    for c in s:
        o = ord(c)
        if (o < 32 and c not in '\n\t\r') or o == 127:
            return False
    good = sum(1 for c in s if c in '\n\t\r ' or 33 <= ord(c) < 127 or ord(c) >= 128)
    return good / len(s) > 0.95


def walk(b, out, depth=0):
    """Generic protobuf wire-format walk; collect (field, text) leaves."""
    i = 0
    n = len(b)
    while i < n:
        tag, i = read_varint(b, i, n)
        field = tag >> 3
        wt = tag & 7
        if field == 0:                  # invalid field number -> desync, stop
            break
        if wt == 0:                     # varint
            _, i = read_varint(b, i, n)
        elif wt == 1:                   # 64-bit
            i += 8
        elif wt == 2:                   # length-delimited
            ln, i = read_varint(b, i, n)
            if ln < 0 or i + ln > n:    # malformed length -> stop this level
                break
            val = b[i:i + ln]
            i += ln
            try:
                txt = val.decode('utf-8')
                if is_texty(txt):
                    out.append((field, txt))
            except UnicodeDecodeError:
                pass
            if depth < 8 and len(val) > 1:
                try:
                    walk(val, out, depth + 1)
                except Exception:
                    pass
        elif wt == 5:                   # 32-bit
            i += 4
        else:                           # 3,4 (groups, deprecated) / unknown -> stop
            break
    return out


def is_noise(s):
    """Structural ids that are never the answer. Deliberately does NOT filter
    base64-ish strings here — a real one-word answer (e.g. 'BOYS_GEMINI_FIXED',
    17 chars no spaces) looks base64-ish too. Opaque response-ids are excluded
    instead by the duplication test in extract_from_steps (they appear once;
    the answer appears twice). base64 filtering is applied only in the fallback."""
    t = s.strip()
    if len(t) < 2:
        return True
    if t in NOISE_EXACT:
        return True
    if UUID_RE.match(t) or t.startswith('bot-'):
        return True
    if HEXID_RE.match(t) or INTID_RE.match(t):
        return True
    return False


def looks_like_opaque_id(t):
    """base64url-ish token with no whitespace/sentence punctuation (response id,
    trace id). Used only in the fallback path, never on the duplication path."""
    return (' ' not in t and '\n' not in t
            and bool(B64ID_RE.match(t)) and not re.search(r'[.,!?:;]', t))


def extract_from_steps(cur, step_type):
    cur.execute(
        "SELECT idx, step_payload FROM steps WHERE step_type=? ORDER BY idx",
        (step_type,),
    )
    chunks = []
    for _idx, payload in cur.fetchall():
        if not payload:
            continue
        leaves = walk(payload, [])
        # The model reply is stored TWICE (content + rendered) in the message
        # sub-message, so it appears with count >= 2; opaque response/trace ids
        # appear once. Select the duplicated text -> robust against short or
        # base64-ish answers. Fallback (format drift): longest non-id leaf.
        counts = {}
        order = []
        for _field, txt in leaves:
            t = txt.strip('\x00').strip()
            if not t or is_noise(t):
                continue
            if t not in counts:
                order.append(t)
            counts[t] = counts.get(t, 0) + 1
        dup = [t for t in order if counts[t] >= 2]
        if dup:
            block = "\n".join(dup)
        else:
            cand = [t for t in order if not looks_like_opaque_id(t)]
            block = max(cand, key=len) if cand else ""
        if block:
            chunks.append(block.strip())
    return "\n".join(c for c in chunks if c).strip()


def main():
    if len(sys.argv) < 2:
        sys.stderr.write("usage: agy-extract.py <conversation.db>\n")
        return 2
    con = sqlite3.connect(sys.argv[1])
    cur = con.cursor()
    # primary: pure model-response steps (type 15)
    text = extract_from_steps(cur, 15)
    if not text:
        # nothing in 15 — this DB format may have shifted; bail loudly
        return 1
    sys.stdout.write(text + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
