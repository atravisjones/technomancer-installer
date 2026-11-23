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
die()  { printf '\n\033[0;31m%s\033[0m\n' "$1" >&2; exit 1; }

# A paid setup gets its download from The Technomancer's server after the plan is checked.
ACCESS="${TM_ACCESS_URL:-https://thetechnomancer.ai}"
ACCESS="${ACCESS%/}"
LICENSE_FILE="$HOME/.technomancer/license.json"

machine_hash() {
  local id="${ASSISTANT_TEST_MACHINE:-}"
  [ -n "$id" ] || id="$(/usr/sbin/ioreg -rd1 -c IOPlatformExpertDevice 2>/dev/null | awk -F'"' '/IOPlatformUUID/{print $4}')"
  [ -n "$id" ] || return 1
  id="$(printf '%s' "$id" | tr '[:upper:]' '[:lower:]')"
  if command -v shasum >/dev/null 2>&1; then printf 'technomancer:%s' "$id" | shasum -a 256 | cut -d' ' -f1
  else printf 'technomancer:%s' "$id" | sha256sum | cut -d' ' -f1; fi
}

# The server's answers are flat and carry no quotes inside a value, so this needs no Python yet.
json_value() { printf '%s' "$1" | sed -n "s/.*\"$2\":\"\([^\"]*\)\".*/\1/p" | head -n 1; }

access_call() {
  local label body
  label="$(scutil --get ComputerName 2>/dev/null || hostname)"
  label="$(printf '%s' "$label" | tr -cd 'A-Za-z0-9 ._-' | cut -c1-60)"
  body="{\"machine\":\"$MACHINE\",\"label\":\"${label:-Mac}\",\"os\":\"mac\"}"
  printf '%s: %s\n' "$2" "$3" | curl -fsS -X POST -H @- -H 'Content-Type: application/json' -d "$body" "$ACCESS/api/access/$1" \
    || die "Setup could not reach The Technomancer to check your plan. Check your internet connection and run this again."
}

# Sets PAID_DOWNLOAD, or leaves it empty when this computer has neither a plan nor a ticket.
paid_download() {
  PAID_DOWNLOAD=""
  local saved="" answer=""
  [ -f "$LICENSE_FILE" ] && saved="$(json_value "$(cat "$LICENSE_FILE")" license)"
  [ -n "$saved" ] || [ -n "${TM_TICKET:-}" ] || return 0
  MACHINE="$(machine_hash)" || die "Setup could not identify this computer. Send a screenshot of this window to whoever sent you the install file."
  if [ -n "$saved" ]; then
    answer="$(access_call update x-tm-license "$saved")" || exit 1
    case "$answer" in *'"ok":true'*)
      PAID_DOWNLOAD="$(json_value "$answer" download)"
      [ -n "$PAID_DOWNLOAD" ] || die "Setup got an unexpected answer from The Technomancer. Run this again in a minute."
      return 0 ;;
    esac
  fi
  if [ -n "${TM_TICKET:-}" ]; then
    answer="$(access_call redeem x-tm-ticket "$TM_TICKET")" || exit 1
    case "$answer" in *'"ok":true'*)
      PAID_DOWNLOAD="$(json_value "$answer" download)"
      [ -n "$PAID_DOWNLOAD" ] || die "Setup got an unexpected answer from The Technomancer. Run this again in a minute."
      mkdir -p "$HOME/.technomancer"
      (umask 077; printf '{"license":"%s","ref":"%s"}\n' "$(json_value "$answer" license)" "$(json_value "$answer" ref)" > "$LICENSE_FILE")
      return 0 ;;
    esac
  fi
  answer="$(json_value "$answer" message)"
  die "${answer:-Setup could not check your plan. Run this again in a minute.}"
}

# Everything runs inside main with stdin closed: this script may be arriving on
# stdin (curl | bash), and a tool that reads stdin would swallow the rest of it.
main() {
printf '\n  The Technomancer: opening setup for your AI assistant. The page will appear in your browser in a moment.\n'

step "Getting the setup page"
fresh="$(mktemp -d "${TMPDIR:-/tmp}/tm.XXXXXX")" || die "Setup could not make a temporary folder."
trap 'rm -rf "$fresh"' EXIT
if [ -n "${ASSISTANT_STARTER_DIR:-}" ]; then
  # The automated test installs the code it just checked out.
  mkdir -p "$fresh/starter"
  tar -C "$ASSISTANT_STARTER_DIR" --exclude=.git -cf - . | tar -xf - -C "$fresh/starter" \
    || die "The setup page could not be copied."
else
  paid_download
  unset TM_TICKET
  case "$PAID_DOWNLOAD" in
    ""|https://*|http://127.0.0.1:*|http://localhost:*) ;;
    *) die "Setup got an unexpected answer from The Technomancer. Run this again in a minute." ;;
  esac
  if [ -n "$PAID_DOWNLOAD" ]; then
    { curl -fsSL "$PAID_DOWNLOAD" -o "$fresh/starter.tgz" && tar -xzf "$fresh/starter.tgz" -C "$fresh"; } \
      || die "The setup page could not be downloaded. Check your internet connection and run this again."
  else
    { curl -fsSL "$TARBALL" -o "$fresh/starter.tgz" && tar -xzf "$fresh/starter.tgz" -C "$fresh"; } \
      || die "This setup needs an active plan. Sign in at $ACCESS/get-started to download your setup file."
  fi
fi
top="$(find "$fresh" -mindepth 1 -maxdepth 1 -type d | head -n 1)"
[ -n "$top" ] && [ -f "$top/install/wizard.py" ] || die "The setup page could not be put in place."
# The working copy is set aside, and put back if the new one cannot take its place.
previous=""
if [ -e "$STARTER" ]; then
  previous="$STARTER.old.$$"
  mv "$STARTER" "$previous" || die "The setup page could not be put in place."
fi
if ! mv "$top" "$STARTER"; then
  rm -rf "$STARTER"
  [ -z "$previous" ] || mv "$previous" "$STARTER"
  die "The setup page could not be put in place. Your current setup was kept."
fi
[ -z "$previous" ] || rm -rf "$previous"
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
