# One-step install for Windows. It only does enough to open the setup page: it downloads
# the starter and finds (or fetches) a Python to run it. The page itself then installs
# Git, Claude Code, the Claude app, Chrome and the rest, and shows each one's progress.
#
# Run it by double-clicking the install file you were sent, or paste this in PowerShell:
#   irm https://raw.githubusercontent.com/atravisjones/technomancer-installer/main/install/install.ps1 | iex
#
# Safe to run again: it fetches the latest starter and keeps your notes.

$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'
# ASSISTANT_STARTER_REF picks another branch or commit; the automated test uses it.
$Ref = if ($env:ASSISTANT_STARTER_REF) { $env:ASSISTANT_STARTER_REF } else { 'main' }
$Zip = "https://github.com/atravisjones/technomancer-installer/archive/$Ref.zip"
$Starter = Join-Path $HOME '.technomancer-setup'

function Write-Step($text) { Write-Host "`n==> $text" -ForegroundColor Cyan }
function Write-Ok($text) { Write-Host "    $text" -ForegroundColor Green }

# The "python" Windows ships is a stub that opens the Store. Only a real one counts.
function Get-Python {
  if ($env:ASSISTANT_FORCE_UV) { return $null }
  foreach ($candidate in @('python', 'py', 'python3')) {
    $cmd = Get-Command $candidate -ErrorAction SilentlyContinue
    if (-not $cmd -or $cmd.Source -like '*\WindowsApps\*') { continue }
    try {
      $version = & $cmd.Source --version 2>$null
      if ($version -match 'Python 3\.(9|\d\d)') { return $cmd.Source }
    } catch { }
  }
  return $null
}

Write-Host "`n  The Technomancer: opening setup for your AI assistant. The page will appear in your browser in a moment." -ForegroundColor White
Write-Host "  If Windows asks for permission to install something later, click Yes.`n"

Write-Step 'Getting the setup page'
$download = Join-Path $env:TEMP 'assistant-starter.zip'
$unpacked = Join-Path $env:TEMP 'assistant-starter-unpacked'
try { Invoke-WebRequest $Zip -OutFile $download -UseBasicParsing }
catch { throw 'The setup page could not be downloaded. Check your internet connection and run this again.' }
if (Test-Path $unpacked) { Remove-Item $unpacked -Recurse -Force }
Expand-Archive $download -DestinationPath $unpacked
if (Test-Path $Starter) { Remove-Item $Starter -Recurse -Force }
Move-Item (Get-ChildItem $unpacked -Directory | Select-Object -First 1).FullName $Starter
Remove-Item $download, $unpacked -Recurse -Force -ErrorAction SilentlyContinue
Write-Ok 'ready'

Write-Step 'Starting it'
$wizard = Join-Path $Starter 'install\wizard.py'
$python = Get-Python
if (-not $python) {
  $env:Path = "$HOME\.local\bin;$env:Path"
  if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    # In its own process: its installer may stop or exit, and this setup must carry on.
    try { powershell -NoProfile -ExecutionPolicy Bypass -Command "`$env:UV_NO_MODIFY_PATH='1'; irm https://astral.sh/uv/install.ps1 | iex" | Out-Null } catch { }
  }
  if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    throw 'Setup could not get the small tool it needs to start. Check your internet connection and run this again.'
  }
}
Write-Ok 'opening your browser'

$env:ASSISTANT_USER_NAME = (Get-Culture).TextInfo.ToTitleCase(($env:USERNAME -split '[\s._]')[0].ToLower())
# ASSISTANT_ANSWERS_FILE (a JSON file of answers) skips the page; the automated test uses it.
$more = @()
if ($env:ASSISTANT_ANSWERS_FILE) { $more = @('--answers', $env:ASSISTANT_ANSWERS_FILE) }
if ($python) { & $python $wizard @more }
else { & uv run --quiet --no-project --python 3.12 $wizard @more }
if ($LASTEXITCODE -ne 0) { throw 'Setup did not finish.' }
