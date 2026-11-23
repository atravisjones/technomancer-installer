#!/usr/bin/env python3
"""Keep one assistant the same on every computer the person uses.

  pull           Bring in what the other computer saved (the start of a session).
  push           Save this computer's notes and send them up (the end of a session).
  resolve        Finish a sync that stopped: resolve path=mine|other|both ...
  keys-send      Lock this computer's .env for one move, and show the code on a local page.
  keys-receive   Unlock it here with that code (read from stdin) and remove the locked copy.
  keys-cancel    Remove a locked copy that was not used.

Every command prints one line of JSON. Nothing is ever force-pushed, and a conflict changes
nothing: the sync stops and the person chooses. The code and the keys are never printed.
"""
import argparse
import base64
import datetime
import json
import os
import re
import secrets
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

TRANSFER_TAG = "assistant-key-transfer"
TRANSFER_FILE = "keys.enc"
TRANSFER_HOURS = 24
PAGE_WAIT = 120  # seconds for the browser to open the code page
CODE_ALPHABET = "23456789ABCDEFGHJKMNPQRSTUVWXYZ"  # nothing that reads like another character
CODE_LENGTH = 16
SECRET_FILE = re.compile(r"(^|/)\.env(\.(?!example$)[^/]+)?$", re.IGNORECASE)  # Windows and Macs ignore case
UNION_FILES = ("sessions/*.md merge=union", "state/decisions.md merge=union", "content/log.md merge=union")
MACHINE_FILES = (".marvin-source", "Open *.cmd", "Open *.command")


def say(state, **more):
    print(json.dumps(dict(state=state, **more)))
    return 0 if state in ("ok", "offline", "no-backup", "nothing", "none") else 1


def git(*args):
    """Never waits on a person: a sign-in problem is reported, not shown as a window mid-chat."""
    env = dict(os.environ, GIT_TERMINAL_PROMPT="0", GCM_INTERACTIVE="never", GIT_MERGE_AUTOEDIT="no",
               GIT_ASKPASS="", SSH_ASKPASS="", SSH_ASKPASS_REQUIRE="never")
    env.setdefault("GIT_SSH_COMMAND", "ssh -o BatchMode=yes")
    try:
        return subprocess.run(["git", *args], capture_output=True, text=True, encoding="utf-8", errors="replace",
                              stdin=subprocess.DEVNULL, timeout=180, env=env)
    except subprocess.TimeoutExpired:
        return subprocess.CompletedProcess(args, 1, "", "timed out")


def gh(*args):
    exe = shutil.which("gh") or str(Path.home() / ".local" / "bin" / ("gh.exe" if os.name == "nt" else "gh"))
    try:
        done = subprocess.run([exe, *args], capture_output=True, text=True, encoding="utf-8", errors="replace",
                              stdin=subprocess.DEVNULL, timeout=120, env=dict(os.environ, GH_NO_UPDATE_NOTIFIER="1"))
    except (OSError, subprocess.TimeoutExpired):
        return False, ""
    return done.returncode == 0, (done.stdout if done.returncode == 0 else done.stderr).strip()


def enter_workspace():
    """Run from the assistant's folder, and only there."""
    top = git("rev-parse", "--show-toplevel").stdout.strip()
    if not top or not (Path(top) / ".assistant-name").exists():
        return False
    os.chdir(top)
    return True


def current_branch():
    return git("symbolic-ref", "--short", "-q", "HEAD").stdout.strip()


def merging():
    return git("rev-parse", "-q", "--verify", "MERGE_HEAD").returncode == 0


def git_file(name):
    return Path(git("rev-parse", "--git-path", name).stdout.strip() or f".git/{name}")


def run_merge(branch):
    """A note marks the merge as ours, so a run that gets cut off can be undone by the next one."""
    git_file("assistant-sync-merge").write_text("1", encoding="utf-8")
    done = git("merge", "--no-edit", f"origin/{branch}")
    if done.returncode == 0:
        git_file("assistant-sync-merge").unlink(missing_ok=True)
    return done


def abort_merge():
    if merging():
        git("merge", "--abort")
    if not merging():
        git_file("assistant-sync-merge").unlink(missing_ok=True)


def keep_note_merges():
    """Two computers adding to a log should both be kept, without asking anyone."""
    path = Path(".gitattributes")
    text = path.read_text(encoding="utf-8") if path.exists() else ""
    missing = [line for line in UNION_FILES if line not in text.splitlines()]
    if missing:
        path.write_text(text.rstrip("\n") + ("\n" if text.strip() else "") + "\n".join(missing) + "\n", encoding="utf-8")


def keep_machine_files_here():
    """Files that only make sense on one computer stay on it, in folders backed up before this rule."""
    path = Path(".gitignore")
    text = path.read_text(encoding="utf-8") if path.exists() else ""
    missing = [line for line in MACHINE_FILES if line not in text.splitlines()]
    if missing:
        path.write_text(text.rstrip("\n") + ("\n" if text.strip() else "") + "\n".join(missing) + "\n", encoding="utf-8")
    git("rm", "-r", "--cached", "-q", "--ignore-unmatch", "--", *MACHINE_FILES)


def save_here():
    """Commit this computer's work. A secrets file is never included, whatever .gitignore says."""
    keep_note_merges()
    keep_machine_files_here()
    git("add", "-A")
    names = git("diff", "--cached", "--name-only", "--no-renames", "-z").stdout.split("\0")
    for name in names:
        if name and SECRET_FILE.search(name):
            git("rm", "--cached", "-q", "--", name)
    if git("diff", "--cached", "--quiet").returncode == 0:
        return True
    return git("commit", "-q", "-m", f"Notes saved {datetime.date.today().isoformat()}").returncode == 0


def reach_github(branch):
    """'here', 'empty' (no copy of this branch yet), 'signed-out' or 'offline'."""
    found = git("ls-remote", "--exit-code", "--heads", "origin", branch)
    if found.returncode == 2:
        return "empty"
    if found.returncode != 0:
        words = found.stderr.lower()
        return "signed-out" if re.search(r"authentication|could not read username|403|not found", words) else "offline"
    fetched = git("fetch", "--no-tags", "-q", "origin", f"+refs/heads/{branch}:refs/remotes/origin/{branch}")
    return "here" if fetched.returncode == 0 else "offline"


def unmerged():
    return [n for n in git("diff", "--name-only", "--diff-filter=U", "-z").stdout.split("\0") if n]


def merge_other(branch):
    """Returns (state, how many saves came in, conflicted files). A conflict is undone at once."""
    count = git("rev-list", "--count", f"HEAD..origin/{branch}").stdout.strip()
    behind = int(count) if count.isdigit() else 0
    if not behind:
        return "ok", 0, []
    if run_merge(branch).returncode == 0:
        return "ok", behind, []
    files = unmerged()
    abort_merge()
    return ("conflict", behind, files) if files else ("error", behind, [])


def send_up(branch):
    """Push, and if the other computer got there first, merge and try once more."""
    for attempt in range(2):
        if git("push", "-u", "origin", branch).returncode == 0:
            return "ok", []
        if attempt:
            break
        reach = reach_github(branch)
        if reach != "here":
            return ("signed-out" if reach == "signed-out" else "offline"), []
        state, _, files = merge_other(branch)
        if state != "ok":
            return state, files
    return "offline", []


def start_sync():
    if not enter_workspace() or not git("remote", "get-url", "origin").stdout.strip():
        return None, say("no-backup")
    branch = current_branch()
    if merging() and git_file("assistant-sync-merge").exists():
        abort_merge()  # an earlier sync was cut off part way: back to where it started
    if not branch or merging():
        return None, say("error", message="The notes are in the middle of another change.")
    if not save_here():
        return None, say("error", message="Your notes could not be saved on this computer.")
    return branch, None


def pull(_args):
    branch, stopped = start_sync()
    if branch is None:
        return stopped
    expire_transfer()
    reach = reach_github(branch)
    if reach == "empty":
        return say("ok", pulled=0)
    if reach != "here":
        return say(reach)
    state, behind, files = merge_other(branch)
    return say(state, pulled=behind if state == "ok" else 0, files=files)


def push(_args):
    branch, stopped = start_sync()
    if branch is None:
        return stopped
    reach = reach_github(branch)
    if reach in ("signed-out", "offline"):
        return say(reach, saved=True)
    pulled = 0
    if reach == "here":
        state, pulled, files = merge_other(branch)
        if state != "ok":
            return say(state, files=files, saved=True)
    state, files = send_up(branch)
    return say(state, pulled=pulled, files=files, saved=True)


def stage_blob(stage, name):
    done = subprocess.run(["git", "show", f":{stage}:{name}"], capture_output=True, stdin=subprocess.DEVNULL)
    return done.stdout if done.returncode == 0 else None


def resolve(args):
    choices = {}
    for item in args.choice:
        name, _, pick = item.rpartition("=")
        if pick not in ("mine", "other", "both") or not name:
            return say("error", message=f"Use path=mine, path=other or path=both, not {item}.")
        choices[name.replace("\\", "/")] = pick
    branch, stopped = start_sync()
    if branch is None:
        return stopped
    # Only the copy the person was shown. Anything newer is caught by send_up and asked about.
    if git("rev-parse", "-q", "--verify", f"refs/remotes/origin/{branch}").returncode != 0:
        return say("offline", saved=True)
    if run_merge(branch).returncode == 0:  # nothing left to choose
        state, files = send_up(branch)
        return say(state, files=files, saved=True)
    files = unmerged()
    if not files or any(name not in choices for name in files):
        abort_merge()
        return say("conflict" if files else "error", files=files)

    def stop(message):
        abort_merge()
        return say("error", message=message, files=files)

    picked = {}
    for name in files:
        mine, other = stage_blob(2, name), stage_blob(3, name)
        pick = choices[name]
        if mine is None or other is None:  # removed or renamed on one side: never lose the copy that exists
            picked[name] = mine if other is None else other
        elif pick == "both":
            if b"\0" in mine or b"\0" in other:
                return stop(f"{name} cannot be combined. Choose mine or other.")
            picked[name] = mine.rstrip() + b"\n\n---\nFrom your other computer:\n\n" + other.lstrip()
        else:
            picked[name] = mine if pick == "mine" else other
    try:
        for name, data in picked.items():
            path = Path(name)
            if data is None:
                git("rm", "-q", "-f", "--", name)
                continue
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
            git("add", "--", name)
    except OSError:
        return stop("That choice could not be written. Nothing was changed.")
    if unmerged() or git("commit", "-q", "--no-edit").returncode != 0:
        return stop("The choice could not be saved.")
    git_file("assistant-sync-merge").unlink(missing_ok=True)
    state, more = send_up(branch)
    return say(state, files=more, saved=True)


# --- Moving the keys ------------------------------------------------------------------
# GitHub holds only a locked file, as a release attachment: unlike a commit, deleting it
# leaves no copy in the history. The code that unlocks it never goes to GitHub or the chat.

def crypto():
    from cryptography.exceptions import InvalidTag
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    from cryptography.hazmat.primitives.kdf.scrypt import Scrypt
    return AESGCM, Scrypt, InvalidTag


def tidy_code(text):
    return re.sub(r"[^A-Z0-9]", "", text.upper())


def new_code():
    return "".join(secrets.choice(CODE_ALPHABET) for _ in range(CODE_LENGTH))


def lock(data, code, repo, created):
    AESGCM, Scrypt, _ = crypto()
    salt, nonce = secrets.token_bytes(16), secrets.token_bytes(12)
    key = Scrypt(salt=salt, length=32, n=2 ** 15, r=8, p=1).derive(tidy_code(code).encode())
    label = json.dumps({"repo": repo.lower(), "created": created}, sort_keys=True).encode()
    locked = AESGCM(key).encrypt(nonce, data, label)
    return json.dumps({"v": 1, "created": created, "salt": base64.b64encode(salt).decode(),
                       "nonce": base64.b64encode(nonce).decode(), "data": base64.b64encode(locked).decode()}).encode()


def unlock(blob, code, repo):
    """Returns (plain bytes, created). Raises InvalidTag for a wrong code or a changed file."""
    AESGCM, Scrypt, _ = crypto()
    box = json.loads(blob)
    key = Scrypt(salt=base64.b64decode(box["salt"]), length=32, n=2 ** 15, r=8, p=1).derive(tidy_code(code).encode())
    label = json.dumps({"repo": repo.lower(), "created": box["created"]}, sort_keys=True).encode()
    return AESGCM(key).decrypt(base64.b64decode(box["nonce"]), base64.b64decode(box["data"]), label), box["created"]


def private_repo():
    worked, out = gh("repo", "view", "--json", "nameWithOwner,isPrivate")
    if not worked:
        return None
    row = json.loads(out)
    return row["nameWithOwner"] if row.get("isPrivate") is True else None


def remove_transfer(repo):
    """True when no locked copy is left. If GitHub could not remove it, the next pull tries again."""
    worked, note = gh("release", "delete", TRANSFER_TAG, "--repo", repo, "--yes", "--cleanup-tag")
    if worked or "not found" in note.lower():
        marker().unlink(missing_ok=True)
        return True
    marker().write_text("0", encoding="utf-8")
    return False


def marker():
    return Path(git("rev-parse", "--git-path", "assistant-key-transfer").stdout.strip() or ".git/assistant-key-transfer")


def expire_transfer():
    """An unused locked copy does not outlive its day."""
    path = marker()
    try:
        if time.time() - float(path.read_text(encoding="utf-8")) < TRANSFER_HOURS * 3600:
            return
    except (OSError, ValueError):
        return
    repo = private_repo()
    if repo:
        remove_transfer(repo)


def env_values(text):
    found = {}
    for line in text.lstrip("\ufeff").splitlines():
        match = re.match(r"\s*(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*=(.*)$", line)
        if match and not line.lstrip().startswith("#"):
            found[match.group(1)] = match.group(2).strip()
    return found


def has_value(value):
    """KEY="" is empty too."""
    return bool(value.strip().strip("\"'").strip())


def write_private(path, text):
    temp = path.with_name(path.name + ".new")
    descriptor = os.open(str(temp), os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    if hasattr(os, "fchmod"):  # a leftover file keeps its old permissions otherwise
        os.fchmod(descriptor, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8", errors="surrogateescape", newline="\n") as out:
        out.write(text)
    os.replace(str(temp), str(path))


def add_missing_keys(path, incoming):
    """Add what this computer lacks. A value already set here is never replaced."""
    text = path.read_bytes().decode("utf-8", "surrogateescape").lstrip("\ufeff") if path.exists() else ""
    have = env_values(text)
    values = env_values(incoming)
    add = {k: v for k, v in values.items() if has_value(v) and not has_value(have.get(k, ""))}
    if not add:
        return 0
    kept = [line for line in text.splitlines()
            if not any(re.match(rf"\s*(?:export\s+)?{re.escape(k)}\s*=", line) for k in add)]
    write_private(path, "\n".join(kept + [f"{k}={v}" for k, v in add.items()]).strip("\n") + "\n")
    return len(add)


CODE_PAGE = """<!doctype html><html lang="en"><head><meta charset="utf-8"><title>Your code</title>
<meta name="viewport" content="width=device-width,initial-scale=1"><style>
body{margin:0;min-height:100vh;display:grid;place-items:center;background:#1C2B3A;color:#F7ECDF;font:18px/1.5 system-ui,sans-serif;padding:16px;box-sizing:border-box}
main{max-width:520px;text-align:center}code{display:block;margin:24px 0;padding:18px;border-radius:12px;background:#F7ECDF;color:#1C2B3A;
font:700 clamp(20px,6vw,32px)/1.2 ui-monospace,Consolas,monospace;letter-spacing:.04em;user-select:all}
p{margin:8px 0}</style></head><body><main><h1>Your code for the other computer</h1><code>__CODE__</code>
<p>Type it into setup on your other computer. It works once and ends in 24 hours.</p>
<p>Do not paste it into a chat or send it to anyone. This page will not show it again.</p></main></body></html>"""


def show_code(code):
    """Show the code on a page only this computer can open, once. It never reaches the chat."""
    path = "/" + secrets.token_urlsafe(24)
    grouped = "-".join(code[i:i + 4] for i in range(0, len(code), 4))
    body = CODE_PAGE.replace("__CODE__", grouped).encode("utf-8")
    shown, claimed, lock = [], [], threading.Lock()

    class Page(BaseHTTPRequestHandler):
        timeout = 5  # a browser can open a connection and send nothing

        def do_GET(self):
            with lock:
                first = self.path == path and not claimed
                if first:
                    claimed.append(True)
            if not first:
                self.send_error(404)
                return
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)
            shown.append(True)

        def log_message(self, *args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Page)
    server.daemon_threads = True
    server.timeout = 1
    try:
        webbrowser.open(f"http://127.0.0.1:{server.server_address[1]}{path}")
        stop_at = time.monotonic() + PAGE_WAIT
        while not shown and time.monotonic() < stop_at:
            server.handle_request()
        if shown:
            time.sleep(1)  # let the page finish arriving before this program ends
    finally:
        server.server_close()
    return bool(shown)


def keys_send(_args):
    if not enter_workspace():
        return say("no-backup")
    env = Path(".env")
    data = env.read_bytes() if env.exists() else b""
    if not any(has_value(v) for v in env_values(data.decode("utf-8", "surrogateescape")).values()):
        return say("nothing")
    repo = private_repo()
    if repo is None:
        return say("error", message="This assistant has no private GitHub copy to send through.")
    code = new_code()
    created = int(time.time())
    remove_transfer(repo)
    with tempfile.TemporaryDirectory() as folder:
        file = Path(folder) / TRANSFER_FILE
        file.write_bytes(lock(data, code, repo, created))
        worked, _ = gh("release", "create", TRANSFER_TAG, str(file), "--repo", repo, "--prerelease", "--latest=false",
                       "--title", "Temporary", "--notes", "A locked file for moving to another computer. It removes itself.")
    if not worked:
        return say("error", message="GitHub would not hold the locked copy.")
    marker().write_text(str(created), encoding="utf-8")
    if not show_code(code):
        remove_transfer(repo)
        return say("error", message="The code page did not open, so the locked copy was removed. Try again.")
    return say("ok", hours=TRANSFER_HOURS)


def keys_receive(_args):
    if not enter_workspace():
        return say("no-backup")
    code = tidy_code(sys.stdin.readline())
    if len(code) != CODE_LENGTH:
        return say("wrong-code")
    repo = private_repo()
    if repo is None:
        return say("error", message="This assistant has no private GitHub copy to read from.")
    _, _, InvalidTag = crypto()
    with tempfile.TemporaryDirectory() as folder:
        worked, _ = gh("release", "download", TRANSFER_TAG, "--repo", repo, "--pattern", TRANSFER_FILE, "--dir", folder)
        file = Path(folder) / TRANSFER_FILE
        if not worked or not file.exists():
            return say("none")
        try:
            data, created = unlock(file.read_bytes(), code, repo)
        except (InvalidTag, ValueError, KeyError, TypeError):
            return say("wrong-code")
    if time.time() - created > TRANSFER_HOURS * 3600:
        remove_transfer(repo)
        return say("expired")
    added = add_missing_keys(Path(".env"), data.decode("utf-8", "surrogateescape"))
    return say("ok", added=added, removed=remove_transfer(repo))


def keys_cancel(_args):
    if not enter_workspace():
        return say("no-backup")
    repo = private_repo()
    if repo is None:
        return say("error", message="This assistant has no private GitHub copy.")
    remove_transfer(repo)
    return say("ok")


def main(argv=None):
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    for name, run in (("pull", pull), ("push", push), ("keys-send", keys_send), ("keys-receive", keys_receive),
                      ("keys-cancel", keys_cancel)):
        sub.add_parser(name).set_defaults(run=run)
    choose = sub.add_parser("resolve")
    choose.add_argument("choice", nargs="+")
    choose.set_defaults(run=resolve)
    args = parser.parse_args(argv)
    return args.run(args)


if __name__ == "__main__":
    sys.exit(main())
