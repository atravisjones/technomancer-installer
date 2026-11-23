#!/usr/bin/env python3
"""Build one client's install files.

    python install/build-installer.py --client path/to/client.json

The client file says what the install file carries. Every field is optional:

    {
      "slug": "acme",                    folder name under dist/ (default: the file's name)
      "company": "Acme Plumbing",        fills in the company name on the setup page
      "industry": "plumbing",            preselects the trade (see INDUSTRIES in wizard.py)
      "crm": "jobber",                   preselects the CRM (see INTEGRATIONS in wizard.py)
      "phone": "callrail",               preselects the phone system
      "github_org": "acme-plumbing",     the company's GitHub organization, if it has one
      "work_domain": "acmeplumbing.com", the email domain people sign in to Claude with
      "contact": "Travis at The Technomancer",   who setup tells people to ask for help
      "tools": "claude",                 assistants ticked to start: claude, gemini, codex, grok
      "bridge_url": "https://...",       the client's data bridge, for the live integrations
      "bridge_token_env": "NAME",        the setting in .env that holds the bridge token
      "pack": "folder"                   company notes (.md) to carry; skills/<name>/SKILL.md become skills
    }

Leave crm and phone out to have the person pick them on the page. The bridge token is read
from the environment or a .env file (current folder first), never from the client file.

Writes to dist/<slug>/ (never committed, the files can hold a token):
    Technomancer Setup.cmd            Windows: double-click
    Technomancer Setup (Mac).zip      Mac: unzip, then open the file inside
"""
import argparse
import base64
import io
import json
import os
import re
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = "https://raw.githubusercontent.com/atravisjones/technomancer-installer/main/install"

# name in the client file -> (setting the install file sets, characters it may hold)
FIELDS = {
    "company": ("TM_COMPANY", r"A-Za-z0-9 &.,-"),  # no quotes: they would break the Mac file
    "industry": ("TM_INDUSTRY", "a-z0-9-"),
    "crm": ("TM_CRM", "a-z0-9-"),
    "phone": ("TM_PHONE", "a-z0-9-"),
    "github_org": ("TM_GITHUB_ORG", "A-Za-z0-9-"),
    "work_domain": ("ASSISTANT_WORK_DOMAIN", "a-z0-9.-"),
    "contact": ("ASSISTANT_HELP_CONTACT", "A-Za-z0-9 .@-"),  # no brackets: they would break the Windows file
    "tools": ("ASSISTANT_DEFAULT_TOOLS", "a-z,"),
    "bridge_url": ("TM_BRIDGE_URL", r"A-Za-z0-9:/._\-"),
}

WINDOWS_HEAD = "@echo off\ntitle The Technomancer: AI assistant setup\n"
WINDOWS_TAIL = """set "ASSISTANT_INSTALL_FILE=%~f0"
powershell -NoProfile -ExecutionPolicy Bypass -Command "[Net.ServicePointManager]::SecurityProtocol='Tls12'; irm {raw}/install.ps1 | iex"
if errorlevel 1 (
  echo.
  echo Setup hit a problem. Take a screenshot of this window and send it to {contact}.
  pause
)
exit /b
"""

# A file that carries a ticket fetches its script from the access server, which checks the ticket first.
ACCESS = "https://thetechnomancer.ai"
WINDOWS_PAID = """set "ASSISTANT_INSTALL_FILE=%~f0"
powershell -NoProfile -ExecutionPolicy Bypass -Command "[Net.ServicePointManager]::SecurityProtocol='Tls12'; $s = Invoke-RestMethod -UseBasicParsing -Uri ($env:TM_ACCESS_URL + '/api/access/script?os=windows') -Headers @{{'x-tm-ticket'=$env:TM_TICKET}}; Invoke-Expression $s"
if errorlevel 1 (
  echo.
  echo Setup stopped. Take a screenshot of this window and send it to {contact}.
  pause
)
exit /b
"""
MAC_PAID = """export ASSISTANT_INSTALL_FILE="$(cd "$(dirname "$0")" && pwd)/$(basename "$0")"
script="$(mktemp "${{TMPDIR:-/tmp}}/tm.XXXXXX")"
printf 'x-tm-ticket: %s\\n' "$TM_TICKET" | curl -fsSL -H @- "$TM_ACCESS_URL/api/access/script?os=mac" -o "$script"
status=$?
if [ "$status" -eq 0 ]; then bash "$script" </dev/null; status=$?; fi
rm -f "$script"
if [ "$status" -ne 0 ]; then
  echo
  echo "Setup stopped. Take a screenshot of this window and send it to {contact}."
  read -r -p "Press Enter to close." _
fi
exit 0
"""

MAC_HEAD = "#!/bin/bash\n"
MAC_TAIL = """export ASSISTANT_INSTALL_FILE="$(cd "$(dirname "$0")" && pwd)/$(basename "$0")"
curl -fsSL {raw}/install.sh | bash
status=$?
if [ "$status" -ne 0 ]; then
  echo
  echo "Setup hit a problem. Take a screenshot of this window and send it to {contact}."
  read -r -p "Press Enter to close." _
fi
exit 0
"""


def find_setting(name):
    if os.environ.get(name):
        return os.environ[name]
    for env in (Path.cwd() / ".env", ROOT / ".env"):
        if env.exists():
            for line in env.read_text(encoding="utf-8").splitlines():
                if line.startswith(name + "="):
                    return line.split("=", 1)[1].strip().strip("\"'")
    return ""


def pack_lines(folder, prefix):
    """The knowledge pack (every .md under the folder) as marked base64 lines."""
    files = sorted(p for p in folder.rglob("*.md"))
    if not files:
        return "", 0
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as z:
        for item in files:
            z.writestr(item.relative_to(folder).as_posix(), item.read_bytes())
    encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
    lines = [prefix + encoded[i:i + 100] for i in range(0, len(encoded), 100)]
    return "\n".join(lines) + "\n", len(files)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--client", required=True, help="the client's JSON file")
    parser.add_argument("--out", help="folder to write to (default: dist/<slug> in this repository)")
    parser.add_argument("--ticket-file", help="a file holding a ticket from content/technomancer/access/grant.mjs")
    args = parser.parse_args()

    source = Path(args.client)
    client = json.loads(source.read_text(encoding="utf-8"))
    slug = re.sub(r"[^a-z0-9-]+", "-", str(client.get("slug") or source.stem).lower()).strip("-") or "client"

    settings = {}
    for field, (name, allowed) in FIELDS.items():
        value = str(client.get(field) or "").strip()
        if not value:
            continue
        if not re.fullmatch(f"[{allowed}]{{1,200}}", value):
            sys.exit(f'"{field}" has characters an install file cannot carry safely: {value!r}')
        settings[name] = value
    org = settings.get("TM_GITHUB_ORG", "")
    if org and not re.fullmatch(r"[A-Za-z0-9](?:[A-Za-z0-9]|-(?=[A-Za-z0-9])){0,38}", org):
        sys.exit('"github_org" is not a GitHub organization name (letters, numbers, single hyphens, at most 39).')
    if settings.get("TM_BRIDGE_URL", "https://").split("://")[0] != "https":
        sys.exit('"bridge_url" must start with https://')

    token_env = str(client.get("bridge_token_env") or "")
    if token_env:
        token = find_setting(token_env)
        if not token:
            sys.exit(f"No bridge token: put {token_env}=... in .env (or the environment), then run this again.")
        if not re.fullmatch(r"[A-Za-z0-9_\-]{20,200}", token):
            sys.exit("That bridge token has characters an install file cannot carry safely.")
        if "TM_BRIDGE_URL" not in settings:
            sys.exit('A bridge token needs a "bridge_url" too.')
        settings["TM_BRIDGE_TOKEN"] = token

    if args.ticket_file:
        ticket = Path(args.ticket_file).read_text(encoding="utf-8").strip()
        if not re.fullmatch(r"[A-Za-z0-9_\-]{32,100}", ticket):
            sys.exit("That ticket file does not hold a ticket.")
        settings.update(TM_TICKET=ticket, TM_ACCESS_URL=ACCESS)

    contact = settings.get("ASSISTANT_HELP_CONTACT", "The Technomancer")
    pack = (source.parent / client["pack"]) if client.get("pack") else None
    win_pack, count = pack_lines(pack, "::PACK:") if pack and pack.is_dir() else ("", 0)
    mac_pack = pack_lines(pack, "#PACK:")[0] if pack and pack.is_dir() else ""

    dist = Path(args.out) if args.out else ROOT / "dist" / slug
    dist.mkdir(parents=True, exist_ok=True)

    windows = dist / "Technomancer Setup.cmd"
    body = WINDOWS_HEAD + "".join(f'set "{k}={v}"\n' for k, v in settings.items()) + (WINDOWS_PAID.format(contact=contact) if args.ticket_file else WINDOWS_TAIL.format(raw=RAW, contact=contact))
    windows.write_bytes((body + win_pack).replace("\n", "\r\n").encode("ascii"))

    # A zip keeps the Mac file's "can be run" flag, which a bare download loses.
    mac_zip = dist / "Technomancer Setup (Mac).zip"
    info = zipfile.ZipInfo("Technomancer Setup.command")
    info.external_attr = 0o100755 << 16
    info.create_system = 3
    mac = MAC_HEAD + "".join(f"export {k}='{v}'\n" for k, v in settings.items()) + (MAC_PAID.format(contact=contact) if args.ticket_file else MAC_TAIL.format(raw=RAW, contact=contact))
    with zipfile.ZipFile(mac_zip, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr(info, mac + mac_pack)

    shown = {k: ("(set)" if k in ("TM_BRIDGE_TOKEN", "TM_TICKET") else v) for k, v in settings.items()}
    print(f"Built for {slug}:\n  {windows}\n  {mac_zip}\n")
    for k, v in shown.items():
        print(f"  {k} = {v}")
    print(f"  knowledge pack: {count} files" if count else "  knowledge pack: none")
    if "TM_BRIDGE_TOKEN" in settings:
        print("\nThese files hold a live token. Share them only with this client.")


if __name__ == "__main__":
    main()
