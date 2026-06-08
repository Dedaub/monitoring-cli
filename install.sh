#!/bin/sh
# install.sh — one-command bootstrap for dedaub-monitoring (macOS / Linux).
#
#   curl -LsSf https://raw.githubusercontent.com/Dedaub/monitoring-cli/main/install.sh | sh
#
# It ensures uv is present (uv then provides a suitable Python itself — you do
# NOT need to install Python separately), installs the CLI straight from the
# public repo, installs the agent skill, and starts the login flow. Re-running
# upgrades an existing install.
set -eu

REPO="https://github.com/Dedaub/monitoring-cli"

info() { printf '\033[1;34m==>\033[0m %s\n' "$1"; }
warn() { printf '\033[1;33mwarning:\033[0m %s\n' "$1" >&2; }
err()  { printf '\033[1;31merror:\033[0m %s\n' "$1" >&2; exit 1; }

# Make a freshly-installed uv (and the CLI it installs) reachable in THIS shell.
# uv's installer and `uv tool` both default to ~/.local/bin; `uv tool dir --bin`
# is authoritative when available but is a newer flag, so we fall back.
add_local_bin_to_path() {
  export PATH="$HOME/.local/bin:$PATH"
  [ -f "$HOME/.local/bin/env" ] && . "$HOME/.local/bin/env"
}

command -v curl >/dev/null 2>&1 || err "curl is required to run this installer."

# uv installs the CLI from a git URL and shells out to system git to do it, so
# git must be present. Auto-installing git differs too much across OSes to do
# reliably, so we fail fast with a clear pointer instead.
if ! command -v git >/dev/null 2>&1; then
  err "git is required (uv uses it to fetch the package). Install it and re-run — macOS: xcode-select --install | Debian/Ubuntu: sudo apt install git | Fedora: sudo dnf install git"
fi

# 1. Ensure uv.
if ! command -v uv >/dev/null 2>&1; then
  info "uv not found — installing it (Astral's official installer)…"
  curl -LsSf https://astral.sh/uv/install.sh | sh
  add_local_bin_to_path
fi
command -v uv >/dev/null 2>&1 || err "uv is still not on PATH. Open a new terminal and re-run this installer."

# 2. Install the CLI from the public repo over HTTPS (no SSH keys, no Python
#    prerequisite — uv fetches the Python pinned by the project).
info "Installing dedaub-monitoring from $REPO …"
uv tool install --force "git+$REPO"

# 3. Make the installed `dedaub-monitoring` reachable now, and persist PATH for
#    future shells so the user doesn't have to open a new terminal.
BIN_DIR="$(uv tool dir --bin 2>/dev/null || true)"
if [ -n "${BIN_DIR:-}" ]; then
  export PATH="$BIN_DIR:$PATH"
else
  add_local_bin_to_path
fi
uv tool update-shell >/dev/null 2>&1 || true

if ! command -v dedaub-monitoring >/dev/null 2>&1; then
  warn "dedaub-monitoring is installed but not on PATH in this shell."
  warn "Open a new terminal, then run: dedaub-monitoring install-skill && dedaub-monitoring login"
  exit 0
fi

# 4. Install the agent skill. Piped (non-TTY) runs take the deterministic
#    'claude + detected agents' default instead of the interactive picker.
info "Installing the agent skill…"
dedaub-monitoring install-skill || warn "Skill install skipped — run 'dedaub-monitoring install-skill' later."

# 5. Authenticate (browser device flow). Prints a URL to open; reads no stdin,
#    so it works even when this script is piped from curl.
info "Starting login (prints a URL to open in your browser)…"
dedaub-monitoring login || warn "Login skipped — run 'dedaub-monitoring login' when ready."

info "Done. Try:  dedaub-monitoring tree"
