#!/usr/bin/env python3
"""Get a release ready for customers.

    python install/release.py "What changed, in one plain line" ["Another line" ...] [--minor | --major]

It bumps VERSION (the last number, unless --minor or --major), adds the lines to the top of
CHANGELOG.md, and refreshes install/known-hashes.json, which lets an update recognise every earlier
version of setup's files so it can replace them safely. Then commit and push. Customers get it the
next time /sync runs, and /start tells them once a week when one is waiting.
"""
import datetime
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def git(*args):
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, check=True).stdout


def known_hashes():
    """Every version of every `.claude` file in this repository's history, by path."""
    found = {}
    for commit in git("rev-list", "--all").decode().split():
        for row in git("-c", "core.quotePath=false", "ls-tree", "-r", commit, "--", ".claude").decode("utf-8", "replace").splitlines():
            meta, path = row.split("\t", 1)
            kind, blob = meta.split()[1:3]
            if kind == "blob":
                found.setdefault(path, set()).add(blob)
    out = {}
    for path, blobs in sorted(found.items()):
        out[path] = sorted({hashlib.sha256(git("cat-file", "-p", b).replace(b"\r\n", b"\n")).hexdigest() for b in blobs})
    return out


def main():
    args = sys.argv[1:]
    lines = [a for a in args if not a.startswith("--")]
    if not lines:
        print(__doc__)
        sys.exit(2)
    old = (ROOT / "VERSION").read_text(encoding="utf-8").strip()
    major, minor, patch = (list(map(int, re.findall(r"\d+", old)[:3])) + [0, 0, 0])[:3]
    if "--major" in args:
        major, minor, patch = major + 1, 0, 0
    elif "--minor" in args:
        minor, patch = minor + 1, 0
    else:
        patch += 1
    new = f"{major}.{minor}.{patch}"
    log = ROOT / "CHANGELOG.md"
    text = log.read_text(encoding="utf-8") if log.exists() else "# What's new\n"
    head, _, rest = text.partition("\n## ")
    entry = f"## {new} - {datetime.date.today().isoformat()}\n\n" + "".join(f"- {line}\n" for line in lines) + "\n"
    log.write_text(head.rstrip("\n") + "\n\n" + entry + (("## " + rest) if rest else ""), encoding="utf-8")
    (ROOT / "VERSION").write_text(new + "\n", encoding="utf-8")
    (ROOT / "install" / "known-hashes.json").write_text(json.dumps(known_hashes(), indent=1) + "\n", encoding="utf-8")
    print(f"{old} -> {new}. Commit VERSION, CHANGELOG.md and install/known-hashes.json, then push.")


if __name__ == "__main__":
    main()
