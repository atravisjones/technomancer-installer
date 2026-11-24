"""Once a week, checks quietly whether a newer version of this assistant is ready.

Prints one line of JSON: {"checked": false} when it is not time yet, else
{"checked": true, "update": true|false, "from": "...", "to": "..."}.
It only downloads the newest setup copy (through get-updates.py); it changes nothing here.
"""
import json
import re
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
WORKSPACE = HERE.parents[1]
STAMP = Path.home() / ".technomancer" / "update-check.json"
WEEK = 7 * 24 * 3600


def version(path):
    try:
        return path.read_text(encoding="utf-8").strip() or "0.0.0"
    except OSError:
        return "0.0.0"


def as_key(text):
    return tuple(int(n) for n in re.findall(r"\d+", text)[:3]) or (0,)


def main():
    now = time.time()
    try:
        last = float(json.loads(STAMP.read_text(encoding="utf-8")).get("at", 0))
    except (OSError, ValueError, TypeError, AttributeError):
        last = 0.0
    if now - last < WEEK and "--now" not in sys.argv:
        print(json.dumps({"checked": False}))
        return
    try:
        got = subprocess.run([sys.executable, str(HERE / "get-updates.py")], capture_output=True, text=True,
                             timeout=300, stdin=subprocess.DEVNULL)
        answer = json.loads(got.stdout.strip().splitlines()[-1])
    except (OSError, ValueError, IndexError, subprocess.SubprocessError):
        answer = {"ok": False, "error": "offline"}
    STAMP.parent.mkdir(parents=True, exist_ok=True)
    # Offline or refused: look again tomorrow rather than in a week.
    STAMP.write_text(json.dumps({"at": now if answer.get("ok") else now - WEEK + 24 * 3600}), encoding="utf-8")
    if not answer.get("ok"):
        print(json.dumps({"checked": True, "update": False, "error": str(answer.get("error", "offline"))}))
        return
    mine = version(WORKSPACE / "VERSION")
    ready = version(Path.home() / ".technomancer-setup" / "VERSION")
    print(json.dumps({"checked": True, "update": as_key(ready) > as_key(mine), "from": mine, "to": ready}))


if __name__ == "__main__":
    main()
