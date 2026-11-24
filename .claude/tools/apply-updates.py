"""Applies the newest setup copy to this assistant folder (step 2 of /sync).

Runs the setup copy's own updater on this folder and passes its one line of JSON through.
"""
import json
import subprocess
import sys
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parents[2]


def main():
    spots = [Path.home() / ".technomancer-setup"]
    try:
        spots.append(Path((WORKSPACE / ".marvin-source").read_text(encoding="utf-8").strip()))
    except OSError:
        pass
    wizard = next((spot / "install" / "wizard.py" for spot in spots if (spot / "install" / "wizard.py").is_file()), None)
    if wizard is None:
        print(json.dumps({"ok": False, "error": "The setup files are not on this computer. Run your setup file again."}))
        sys.exit(1)
    done = subprocess.run([sys.executable, str(wizard), "--update", "--folder", str(WORKSPACE)],
                          capture_output=True, text=True, encoding="utf-8", errors="replace", stdin=subprocess.DEVNULL)
    lines = [line for line in done.stdout.splitlines() if line.startswith("{")]
    print(lines[-1] if lines else json.dumps({"ok": False, "error": "The update did not answer. Your assistant still works. Try again later."}))
    sys.exit(done.returncode)


if __name__ == "__main__":
    main()
