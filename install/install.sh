#!/bin/bash
# One-step install for Mac. It only does enough to open the setup page: it downloads
# the starter and finds (or fetches) a Python to run it. The page itself then installs
# Claude Code, the Claude app, Chrome and the rest, and shows each one's progress.
#
# Run it by opening the install file you were sent, or paste this in Terminal:
#   curl -fsSL https://raw.githubusercontent.com/atravisjones/technomancer-installer/main/install/install.sh | bash
#
# Safe to run again: it fetches the latest starter and keeps your notes.

set -u
# ASSISTANT_STARTER_REF picks another branch or commit; the automated test uses it.
TARBALL="https://codeload.github.com/atravisjones/technomancer-installer/tar.gz/${ASSISTANT_STARTER_REF:-main}"
STARTER="$HOME/.technomancer-setup"
export PATH="$HOME/.local/bin:/opt/homebrew/bin:/usr/local/bin:$PATH"

step() { printf '\n\033[1;36m==> %s\033[0m\n' "$1"; }
ok()   { printf '    \033[0;32m%s\033[0m\n' "$1"; }
die()  { printf '\n\033[0;31m%s\033[0m\n' "$1"; exit 1; }

# Everything runs inside main with stdin closed: this script may be arriving on
# stdin (curl | bash), and a tool that reads stdin would swallow the rest of it.
main() {
printf '\n  The Technomancer: opening setup for your AI assistant. The page will appear in your browser in a moment.\n'

step "Getting the setup page"
fresh="$(mktemp -d)"
curl -fsSL "$TARBALL" | tar -xz -C "$fresh" \
  || die "The setup page could not be downloaded. Check your internet connection and run this again."
rm -rf "$STARTER"
mv "$fresh"/technomancer-installer-* "$STARTER" || die "The setup page could not be put in place."
rm -rf "$fresh"
ok "ready"

# Apple's python3 is a stub that starts a long developer-tools download. Only use it
# when those tools are already here; otherwise fetch a small Python of our own.
step "Starting it"
if [ -z "${ASSISTANT_FORCE_UV:-}" ] && xcode-select -p >/dev/null 2>&1 && command -v python3 >/dev/null 2>&1; then
  runner=(python3)
else
  if ! command -v uv >/dev/null 2>&1; then
    curl -LsSf https://astral.sh/uv/install.sh | env UV_NO_MODIFY_PATH=1 sh >/dev/null 2>&1 \
      || die "Setup could not get the small tool it needs to start. Check your internet connection and run this again."
  fi
  command -v uv >/dev/null 2>&1 || die "Setup could not start. Send a screenshot of this window to whoever sent you the install file."
  runner=(uv run --quiet --no-project --python 3.12)
fi
ok "opening your browser"

first="$(id -F 2>/dev/null | awk '{print $1}')"
export ASSISTANT_USER_NAME="${first:-}"
# ASSISTANT_ANSWERS_FILE (a JSON file of answers) skips the page; the automated test uses it.
if [ -n "${ASSISTANT_ANSWERS_FILE:-}" ]; then
  "${runner[@]}" "$STARTER/install/wizard.py" --answers "$ASSISTANT_ANSWERS_FILE" || die "Setup did not finish."
else
  "${runner[@]}" "$STARTER/install/wizard.py" || die "Setup did not finish."
fi
}

main "$@" </dev/null
