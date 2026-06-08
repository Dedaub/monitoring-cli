# install.ps1 — one-command bootstrap for dedaub-monitoring (Windows).
#
#   powershell -ExecutionPolicy ByPass -c "irm https://raw.githubusercontent.com/Dedaub/monitoring-cli/main/install.ps1 | iex"
#
# It ensures uv is present (uv then provides a suitable Python itself — you do
# NOT need to install Python separately), installs the CLI straight from the
# public repo, installs the agent skill, and starts the login flow. Re-running
# upgrades an existing install.
$ErrorActionPreference = 'Stop'

$Repo = 'https://github.com/Dedaub/monitoring-cli'

function Info($m) { Write-Host "==> $m" -ForegroundColor Blue }
function Warn($m) { Write-Host "warning: $m" -ForegroundColor Yellow }

# Make a freshly-installed uv (and the CLI it installs) reachable in THIS session.
# uv's installer and `uv tool` both default to %USERPROFILE%\.local\bin.
function Add-LocalBinToPath {
  $env:Path = "$env:USERPROFILE\.local\bin;$env:Path"
}

function Have($name) { [bool](Get-Command $name -ErrorAction SilentlyContinue) }

# uv installs the CLI from a git URL and shells out to system git to do it, so
# git must be present. Auto-installing git is left to the user (Windows has no
# universal one-liner for it), so we fail fast with a clear pointer instead.
if (-not (Have 'git')) {
  throw "git is required (uv uses it to fetch the package). Install Git for Windows ('winget install Git.Git' or https://git-scm.com/download/win), then re-run."
}

# 1. Ensure uv.
if (-not (Have 'uv')) {
  Info "uv not found — installing it (Astral's official installer)…"
  powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
  Add-LocalBinToPath
}
if (-not (Have 'uv')) {
  throw "uv is still not on PATH. Open a new terminal and re-run this installer."
}

# 2. Install the CLI from the public repo over HTTPS (no SSH keys, no Python
#    prerequisite — uv fetches the Python pinned by the project).
Info "Installing dedaub-monitoring from $Repo …"
uv tool install --force "git+$Repo"
if ($LASTEXITCODE -ne 0) { throw "uv failed to install the CLI (exit $LASTEXITCODE)." }

# 3. Make the installed `dedaub-monitoring` reachable now, and persist PATH for
#    future shells so the user doesn't have to open a new terminal.
$BinDir = (uv tool dir --bin 2>$null)
if ($LASTEXITCODE -eq 0 -and $BinDir) {
  $env:Path = "$($BinDir.Trim());$env:Path"
} else {
  Add-LocalBinToPath
}
uv tool update-shell 2>$null | Out-Null

if (-not (Have 'dedaub-monitoring')) {
  Warn "dedaub-monitoring is installed but not on PATH in this session."
  Warn "Open a new terminal, then run: dedaub-monitoring install-skill ; dedaub-monitoring login"
  return
}

# 4. Install the agent skill. Non-interactive runs take the deterministic
#    'claude + detected agents' default instead of the interactive picker.
Info "Installing the agent skill…"
try { dedaub-monitoring install-skill } catch { Warn "Skill install skipped — run 'dedaub-monitoring install-skill' later." }

# 5. Authenticate (browser device flow). Prints a URL to open; reads no stdin.
Info "Starting login (prints a URL to open in your browser)…"
try { dedaub-monitoring login } catch { Warn "Login skipped — run 'dedaub-monitoring login' when ready." }

Info "Done. Try:  dedaub-monitoring tree"
