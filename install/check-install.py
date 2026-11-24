#!/usr/bin/env python3
"""Checks what the installer built, for the automated test.

    python check-install.py first    after the first run
    python check-install.py again    after a second run over a changed workspace
    python check-install.py agy      after a run with Antigravity as the main assistant (folder ~/nova)
    python check-install.py codex    after a run with Codex as the main assistant (folder ~/sol)
"""
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

home = Path.home()
work = home / "friday"
failed = []
notes = []


def check(label, ok):
    print(("  ok    " if ok else "  FAIL  ") + label)
    if not ok:
        failed.append(label)


def note(label, ok):
    """Something worth knowing that the test machine may not be able to do."""
    print(("  ok    " if ok else "  note  ") + label)
    if not ok:
        notes.append(label)


def read(path):
    return path.read_text(encoding="utf-8") if path.exists() else ""


def finish():
    print()
    if notes:
        print("Not done on this test machine: " + "; ".join(notes))
    if failed:
        print(str(len(failed)) + " check(s) failed: " + "; ".join(failed))
        sys.exit(1)
    print("All checks passed.")
    sys.exit(0)


def codex_settings():
    text = read(home / ".codex" / "config.toml")
    return text, text.split("\n[", 1)[0]


def shortcut(name):
    """What the shortcut runs. On a Mac it is an app in ~/Applications: the Desktop would ask for permission."""
    if sys.platform == "darwin":
        return read(home / "Applications" / f"{name}.app" / "Contents" / "Resources" / "open.command")
    ending = ".cmd" if os.name == "nt" else ".command"
    for folder in [home / "Desktop"] + sorted(home.glob("OneDrive*/Desktop")):
        if (folder / f"{name}{ending}").exists():
            return read(folder / f"{name}{ending}")
    return ""


def offered(ext):
    """Chrome has been asked to offer this extension (Chrome's own external-extension route)."""
    if os.name == "nt":
        import winreg
        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Google\Chrome\Extensions" + "\\" + ext)
            return "clients2.google.com" in winreg.QueryValueEx(key, "update_url")[0]
        except OSError:
            return False
    return "clients2.google.com" in read(
        home / "Library" / "Application Support" / "Google" / "Chrome" / "External Extensions" / (ext + ".json"))


if sys.argv[1:] == ["codex"]:
    sol = home / "sol"
    ending = ".cmd" if os.name == "nt" else ".command"
    print("Codex as the main assistant")
    check("workspace folder ~/sol", (sol / "CLAUDE.md").exists() and "SOL" in read(sol / "CLAUDE.md"))
    check("Codex is pointed at the notes", "CLAUDE.md" in read(sol / "AGENTS.md"))
    check("skills copied where Codex looks", (sol / ".agents" / "skills" / "github-team" / "SKILL.md").exists())
    start = read(sol / ".agents" / "skills" / "start" / "SKILL.md")
    check("/start and /save are skills", start.startswith("---\nname: start\ndescription:")
          and (sol / ".agents" / "skills" / "save" / "SKILL.md").exists())
    check("ChatGPT has $publish", "Use when the person types /publish" in read(sol / ".agents" / "skills" / "publish" / "SKILL.md"))
    check("the folder's Open file opens the ChatGPT app", "codex app ." in read(sol / f"Open Codex{ending}"))
    check("shortcut opens the ChatGPT app", "codex app ." in shortcut("Sol"))
    whole, top = codex_settings()
    check("Codex never asks", 'approval_policy = "never"' in top and 'sandbox_mode = "danger-full-access"' in top)
    check("Codex's settings are written once", whole.count("approval_policy") == 1)
    check("Codex trusts the folder", ("sol']" in whole.lower() or 'sol"]' in whole.lower()) and 'trust_level = "trusted"' in whole)
    check("Claude's color modes left out", not (sol / ".mods").exists())
    guide = read(sol / "START-HERE.md")
    check("START-HERE teaches ChatGPT's commands ($start, $save, /compact, /new)",
          all(c in guide for c in ("`$start`", "`$save`", "`/compact`", "`/new`")) and "`/start`" not in guide)
    first = read(sol / "state" / "first-chat.md")
    check("first chat covers ChatGPT", "@Chrome" in first and "Plugins" in first and "`$start`" in first)
    check("ChatGPT's $start runs the first chat", "state/first-chat.md" in start)
    check("pending CRM key saved", "JOBBER_API_KEY=test_jobber_key_not_real_123" in read(sol / ".env"))
    check("pending systems marked in CLAUDE.md", "Jobber" in read(sol / "CLAUDE.md") and "JOBBER_API_KEY" in read(sol / "CLAUDE.md"))
    check("no live skill for a pending CRM", not (sol / ".claude" / "skills" / "crm-roofr").exists())
    guide = read(sol / ".claude" / "skills" / "connect-crm" / "SKILL.md")
    check("CRM connection guide written, and Codex has it", "Jobber" in guide and "name: connect-crm" in guide
          and "Jobber" in read(sol / ".agents" / "skills" / "connect-crm" / "SKILL.md"))
    check("guide never names an outside automation service", "zapier" not in guide.lower())
    spot = (Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "OpenAI" / "Codex" / "bin" / "codex.exe") if os.name == "nt" \
        else (home / ".local" / "bin" / "codex")
    note("Codex installed", shutil.which("codex") is not None or spot.exists())
    check("ChatGPT extension offered to Chrome", offered("hehggadaopoacecdllhhajmbjkdcmajg"))
    finish()

if sys.argv[1:] == ["agy"]:
    nova = home / "nova"
    ending = ".cmd" if os.name == "nt" else ".command"
    print("Antigravity as the main assistant")
    check("workspace folder ~/nova", (nova / "CLAUDE.md").exists() and "NOVA" in read(nova / "CLAUDE.md"))
    check("Antigravity is pointed at the notes", "CLAUDE.md" in read(nova / "GEMINI.md"))
    start = read(nova / ".agents" / "skills" / "start" / "SKILL.md")
    check("/start and /save are skills", start.startswith("---\nname: start\ndescription:")
          and (nova / ".agents" / "skills" / "save" / "SKILL.md").exists())
    check("Antigravity has /publish", "Use when the person types /publish" in read(nova / ".agents" / "skills" / "publish" / "SKILL.md"))
    guide = read(nova / "START-HERE.md")
    check("START-HERE teaches /start, /save, /compact and the + button, not $start",
          all(c in guide for c in ("`/start`", "`/save`", "`/compact`", "+")) and "$start" not in guide)
    first = read(nova / "state" / "first-chat.md")
    check("first chat covers Antigravity", "Enable Remote Control" in first and "antigravity.google" in first
          and "{" not in first and "}" not in first)
    opener = read(nova / f"Open Antigravity{ending}")
    check("the folder's Open file opens the app, else the terminal tool", "Antigravity" in opener and "agy" in opener)
    note("shortcut opens the app", "Antigravity" in shortcut("Nova"))
    try:
        agy_settings = json.loads(read(home / ".gemini" / "antigravity-cli" / "settings.json") or "{}")
    except ValueError:
        agy_settings = {}
    check("Antigravity never asks, and trusts the folder", agy_settings.get("toolPermission") == "always-proceed"
          and str(nova) in agy_settings.get("trustedWorkspaces", []))
    team = read(nova / ".claude" / "skills" / "team" / "SKILL.md")
    check("team skill lists only the picked assistants, not the main one",
          "name: team" in team and "grok -p" in team and "agy -p" not in team
          and "codex exec" not in team and "claude -p" not in team)
    check("team skill reaches Antigravity's copy", "grok -p" in read(nova / ".agents" / "skills" / "team" / "SKILL.md"))
    check("reviews go through the review room", "review_room.py --tool grok" in team and "never ask for a second opinion" in team)
    check("the review room ships with both copies of the skill",
          all("--self-test" in read(nova / where / "skills" / "team" / "review_room.py") for where in (".claude", ".agents")))
    check("CLAUDE.md mentions the team skill", "skills/team/SKILL.md" in read(nova / "CLAUDE.md"))
    check("Claude's color modes left out", not (nova / ".mods").exists())
    note("Antigravity installed", shutil.which("agy") is not None)
    finish()

print("Workspace")
check("setup downloaded to ~/.technomancer-setup", (home / ".technomancer-setup" / "install" / "wizard.py").exists())
check("workspace folder ~/friday", work.is_dir())
check("CLAUDE.md names the assistant and the person", "FRIDAY" in read(work / "CLAUDE.md") and "Pat" in read(work / "CLAUDE.md"))
check("START-HERE.md written", "/save" in read(work / "START-HERE.md") and "/compact" in read(work / "START-HERE.md"))
check("/save command present, /end gone",
      (work / ".claude" / "commands" / "save.md").exists() and not (work / ".claude" / "commands" / "end.md").exists())
check("Roofr reads through the person's own tab, CTM through its skill",
      "app.roofr.com" in read(work / ".claude" / "skills" / "connect-crm" / "SKILL.md")
      and (work / ".claude" / "skills" / "phone-ctm" / "SKILL.md").exists()
      and not (work / ".claude" / "skills" / "crm-roofr").exists())
check("github-team skill present", (work / ".claude" / "skills" / "github-team" / "SKILL.md").exists())
check("graphify skill present", (work / ".claude" / "skills" / "graphify" / "SKILL.md").exists())
check("code maps stay out of git", "graphify-out/" in read(work / ".gitignore").split())
check("/publish keeps code maps offline", "graphify-out/" in read(work / ".claude" / "commands" / "publish.md"))
first = read(work / "state" / "first-chat.md")
check("first chat gets to know them, shows Chrome and the phone, checks the tools",
      all(words in first for words in ("Get to know them", "outside work", "tab group", "/remote-control",
                                       "Check the tools", "Part 3 of `CLAUDE.md`", "@Chrome", "vercel whoami"))
      and "{" not in first)
check("/publish command present, with the Supabase rules",
      all(words in read(work / ".claude" / "commands" / "publish.md") for words in ("vercel --prod --yes", "Row Level Security", "anon")))
check("optional extras moved to the first chat", all(words in first for words in (
    "Optional extras", "Let ChatGPT use this computer", "add-assistant.md")))
check("/add-assistant command present", "--add-assistant" in read(work / ".claude" / "commands" / "add-assistant.md"))
check("/get-help opens one-time remote support", "remotedesktop.google.com/support" in read(work / ".claude" / "commands" / "get-help.md"))
check("START-HERE explains remote help", "/get-help" in read(work / "START-HERE.md"))
check("version recorded", read(work / "VERSION").strip() == read(home / ".technomancer-setup" / "VERSION").strip() != "")
check("setup's files are recorded for safe updates", ".claude/commands/start.md" in read(work / ".assistant-managed.json"))
check("/sync applies updates with its own helper", "apply-updates.py" in read(work / ".claude" / "commands" / "sync.md")
      and (work / ".claude" / "tools" / "apply-updates.py").exists())
check("/start checks for updates", "check-updates.py" in read(work / ".claude" / "commands" / "start.md")
      and (work / ".claude" / "tools" / "check-updates.py").exists())
check("/start runs the first chat once", "state/first-chat.md" in read(work / ".claude" / "commands" / "start.md"))
check("swarm layer left out", not (work / ".claude" / "agents" / "the-boys.md").exists())
check("bridge token in .env", "TM_BRIDGE_TOKEN=test_token_not_real_0000000000" in read(work / ".env"))
check("bridge address in .env", "TM_BRIDGE_URL=https://bridge.example.com/api" in read(work / ".env"))
check("token not in CLAUDE.md or START-HERE.md",
      "test_token" not in read(work / "CLAUDE.md") + read(work / "START-HERE.md"))

print("Role kit, business and company knowledge")
claude_md = read(work / "CLAUDE.md")
check("role focus in CLAUDE.md", "Running appointments and closing jobs" in claude_md)
check("CRM name in CLAUDE.md", "Pat Example" in claude_md)
check("company and trade in CLAUDE.md", "Example Roofing Co" in claude_md and "**Trade:** Roofing" in claude_md)
check("systems in CLAUDE.md", "connect-crm" in claude_md and "phone-ctm" in claude_md)
check("company settings saved", json.loads(read(work / ".company.json") or "{}").get("crm") == "roofr")
check("role examples in START-HERE.md", "Show me my open jobs" in read(work / "START-HERE.md"))
check("knowledge pack unpacked", (work / "company" / "README.md").exists() and (work / "company" / "sops" / "example.md").exists())
check("CLAUDE.md points at the pack", "company/README.md" in claude_md)

print("Color modes")
topics = read(work / ".mods" / "session-tint" / "hooks" / "topics.js")
check("mod copied into the workspace", (work / ".mods" / "session-tint" / "hooks" / "register.ts").exists())
check("topics hold the assistant and the company", '"label": "Friday"' in topics and '"label": "Example Roofing Co"' in topics)
check("assistant color is teal", "#1e8c80" in topics)

print("Claude settings")
try:
    settings = json.loads(read(home / ".claude" / "settings.json") or "{}")
except ValueError:
    settings = {}
check("bypass permissions on", settings.get("permissions", {}).get("defaultMode") == "bypassPermissions")
check("remote control on", settings.get("remoteControlAtStartup") is True)
check("starting model set for the role", settings.get("model") == "sonnet")
check("chat history kept", settings.get("cleanupPeriodDays") == 3650)
check("mod folder registered", "session-tint" in settings.get("env", {}).get("CLAUDE_CODE_PLUGIN_DIRS", ""))

print("Antigravity")
try:
    agy = json.loads(read(home / ".gemini" / "antigravity-cli" / "settings.json") or "{}")
except ValueError:
    agy = {}
check("Antigravity never asks", agy.get("toolPermission") == "always-proceed")
check("Antigravity trusts the assistant's folder", str(work) in agy.get("trustedWorkspaces", []))
check("Antigravity is pointed at CLAUDE.md", "CLAUDE.md" in read(work / "GEMINI.md"))

print("Other assistants")
check("Codex and Grok are pointed at CLAUDE.md", "CLAUDE.md" in read(work / "AGENTS.md"))
check("all three are pointed at the skills", all(".claude/skills/" in read(work / f) for f in ("AGENTS.md", "GEMINI.md")))
local = Path(os.environ.get("LOCALAPPDATA", ""))
ending = ".cmd" if os.name == "nt" else ".command"
for label, command, flag, windows_spot, other_spot in (
        ("Antigravity", "agy", "", local / "agy" / "bin" / "agy.exe", home / ".local" / "bin" / "agy"),
        ("Codex", "codex", "",
         local / "Programs" / "OpenAI" / "Codex" / "bin" / "codex.exe", home / ".local" / "bin" / "codex"),
        ("Grok", "grok", "--always-approve", home / ".grok" / "bin" / "grok.exe", home / ".grok" / "bin" / "grok")):
    opener = read(work / f"Open {label}{ending}")
    check(f"{label} has a file that opens it in the folder", command in opener and "cd " in opener)
    if flag:
        check(f"{label} never asks", flag in opener)
    if os.name != "nt":
        check(f"{label}'s file can be run", os.access(work / f"Open {label}{ending}", os.X_OK))
    note(f"{label} installed", shutil.which(command.split()[0]) is not None or (windows_spot if os.name == "nt" else other_spot).exists())
check("Codex beside Claude opens in a terminal, not the ChatGPT app", "codex app" not in read(work / f"Open Codex{ending}"))
check("no Open Claude file when Claude is the main assistant", not (work / f"Open Claude{ending}").exists())
whole, top = codex_settings()
check("Codex never asks, in the app too", 'approval_policy = "never"' in top and 'sandbox_mode = "danger-full-access"' in top)
check("Codex trusts the assistant's folder", ("friday']" in whole.lower() or 'friday"]' in whole.lower()) and 'trust_level = "trusted"' in whole)
check("Codex's settings are written once", whole.count("approval_policy") == 1)
check("Codex has the skills too", "app.roofr.com" in read(work / ".agents" / "skills" / "connect-crm" / "SKILL.md")
      and (work / ".agents" / "skills" / "phone-ctm" / "SKILL.md").exists())

print("Shortcut and tools")
check("shortcut made", bool(shortcut("Friday")))
if sys.platform == "darwin":
    check("nothing written to the Mac's Desktop", not (home / "Desktop" / "Friday.command").exists())
os.environ["PATH"] = str(home / ".local" / "bin") + os.pathsep + os.environ.get("PATH", "")
claude = shutil.which("claude")
check("Claude Code installed", claude is not None)
if claude:
    version = subprocess.run([claude, "--version"], capture_output=True, text=True, encoding="utf-8", errors="replace")
    check("Claude Code runs (" + version.stdout.strip()[:40] + ")", version.returncode == 0)
    valid = subprocess.run([claude, "plugin", "validate", str(work / ".mods" / "session-tint")],
                           capture_output=True, text=True, encoding="utf-8", errors="replace")
    check("Claude accepts the color mod", valid.returncode == 0)
check("git on this machine", shutil.which("git") is not None)
note("GitHub tool on this machine", shutil.which("gh") is not None or (home / ".local" / "bin" / ("gh.exe" if os.name == "nt" else "gh")).exists())
note("node on this machine", shutil.which("node") is not None)
(check if os.environ.get("CI") and not os.environ.get("ASSISTANT_SKIP_INSTALLS") else note)(
    "graphify on this machine", shutil.which("graphify") is not None or any(
        (home / ".local" / "bin" / name).exists() for name in ("graphify", "graphify.exe")))
if sys.platform == "darwin":
    note("Claude desktop app installed", Path("/Applications/Claude.app").exists())
    note("Chrome installed", Path("/Applications/Google Chrome.app").exists())
elif os.name == "nt":
    local = Path(os.environ.get("LOCALAPPDATA", ""))
    note("Claude desktop app installed", (local / "AnthropicClaude" / "claude.exe").exists())

print("Chrome")
check("Claude extension offered to Chrome", offered("fcoeoabgfenejglbffodgkkbkcdhcgfn"))

if sys.argv[1:] == ["again"]:
    print("Second run")
    check("the person's own note survived", "my own note" in read(work / "state" / "goals.md"))
    check("settings backup kept", (home / ".claude" / "settings.json.before-setup").exists())
    check("token still there once", read(work / ".env").count("TM_BRIDGE_TOKEN=") == 1)
    check("systems section written once", read(work / "CLAUDE.md").count("<!-- systems:start -->") == 1)

finish()
