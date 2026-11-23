"""Gets the newest setup files for /sync after checking this computer's plan.

Prints one line of JSON: {"ok": true} or {"ok": false, "error": ..., "message": ...}.
It only ever replaces the setup copy in ~/.technomancer-setup, never this folder.
"""
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from pathlib import Path

SITE = os.environ.get("TM_ACCESS_URL", "https://thetechnomancer.ai").rstrip("/")
MOST_BYTES = 200 * 1024 * 1024


def finish(ok, error="", message=""):
    print(json.dumps({"ok": True} if ok else {"ok": False, "error": error, "message": message}))
    sys.exit(0 if ok else 1)


def machine_id():
    named = os.environ.get("ASSISTANT_TEST_MACHINE", "")
    if named:
        return named
    if os.name == "nt":
        import winreg
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Cryptography", 0, winreg.KEY_READ | winreg.KEY_WOW64_64KEY) as key:
            return winreg.QueryValueEx(key, "MachineGuid")[0]
    text = subprocess.run(["/usr/sbin/ioreg", "-rd1", "-c", "IOPlatformExpertDevice"], capture_output=True, text=True, timeout=10).stdout
    for line in text.splitlines():
        if "IOPlatformUUID" in line:
            return line.split('"')[-2]
    raise OSError("no computer ID")


def safe_address(url):
    parsed = urllib.parse.urlparse(url)
    return parsed.scheme == "https" or (parsed.scheme == "http" and parsed.hostname in ("127.0.0.1", "localhost"))


def main():
    home = Path.home()
    try:
        saved = json.loads((home / ".technomancer" / "license.json").read_text(encoding="utf-8-sig"))
        license_key = str(saved["license"])
    except (OSError, ValueError, KeyError, TypeError):
        finish(False, "no_license", f"This computer has no plan on file. Sign in at {SITE}/get-started and run a fresh setup file.")

    try:
        machine = hashlib.sha256(("technomancer:" + machine_id().strip().lower()).encode()).hexdigest()
    except (OSError, IndexError, subprocess.SubprocessError):
        finish(False, "offline", "This computer could not be identified, so updates were skipped.")

    request = urllib.request.Request(
        f"{SITE}/api/access/update", method="POST",
        data=json.dumps({"machine": machine, "os": "windows"}).encode(),  # always a zip, on any computer
        headers={"Content-Type": "application/json", "x-tm-license": license_key, "User-Agent": "technomancer-updates"})
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            answer = json.loads(response.read(64 * 1024))
    except (OSError, ValueError):
        finish(False, "offline", "Could not reach the update server. Your assistant still works. Try again later.")
    if not answer.get("ok"):
        finish(False, str(answer.get("error", "unknown")), str(answer.get("message", "Updates are not available.")))
    if not safe_address(str(answer.get("download", ""))):
        finish(False, "offline", "The update server sent an unexpected answer, so nothing was changed.")

    target = home / ".technomancer-setup"
    work = Path(tempfile.mkdtemp(prefix=".technomancer-update-", dir=home))
    old = None
    try:
        archive = work / "update.zip"
        got = 0
        fetch = urllib.request.Request(answer["download"], headers={"User-Agent": "technomancer-updates"})
        with urllib.request.urlopen(fetch, timeout=120) as response, open(archive, "wb") as out:
            while chunk := response.read(1024 * 1024):
                got += len(chunk)
                if got > MOST_BYTES:
                    raise ValueError("too large")
                out.write(chunk)
        unpacked = work / "new"
        with zipfile.ZipFile(archive) as bundle:
            if sum(item.file_size for item in bundle.infolist()) > MOST_BYTES * 3:
                raise ValueError("too large")
            bundle.extractall(unpacked)  # extractall drops any path that climbs out of the folder
        folders = [p for p in unpacked.iterdir() if p.is_dir()]
        if len(folders) != 1 or not (folders[0] / "install" / "wizard.py").is_file():
            raise ValueError("not a setup copy")
        if target.exists():
            old = work / "old"
            target.rename(old)
        try:
            folders[0].rename(target)
        except OSError:
            if old:
                old.rename(target)
                old = None
            raise
    except (OSError, ValueError, zipfile.BadZipFile):
        finish(False, "offline", "The update did not finish, so your current version was kept. Try again later.")
    finally:
        shutil.rmtree(work, ignore_errors=True)
    finish(True)


if __name__ == "__main__":
    main()
