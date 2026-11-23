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

# A paid setup gets its download from The Technomancer's server after the plan is checked.
$Access = if ($env:TM_ACCESS_URL) { $env:TM_ACCESS_URL.TrimEnd('/') } else { 'https://thetechnomancer.ai' }
$LicenseFile = Join-Path (Join-Path $HOME '.technomancer') 'license.json'

function Get-MachineHash {
  $id = if ($env:ASSISTANT_TEST_MACHINE) { $env:ASSISTANT_TEST_MACHINE } else { (Get-ItemProperty 'HKLM:\SOFTWARE\Microsoft\Cryptography' -Name MachineGuid).MachineGuid }
  $hash = [Security.Cryptography.SHA256]::Create().ComputeHash([Text.Encoding]::UTF8.GetBytes('technomancer:' + "$id".Trim().ToLower()))
  return -join ($hash | ForEach-Object { $_.ToString('x2') })
}

function Invoke-Access($Action, $Header, $Value) {
  $body = @{ machine = (Get-MachineHash); label = "$env:COMPUTERNAME"; os = 'windows' } | ConvertTo-Json -Compress
  try { return Invoke-RestMethod -Method Post -Uri "$Access/api/access/$Action" -Headers @{ $Header = $Value } -ContentType 'application/json' -Body $body -UseBasicParsing }
  catch { throw 'Setup could not reach The Technomancer to check your plan. Check your internet connection and run this again.' }
}

function Get-PaidDownload {
  [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
  $saved = $null
  if (Test-Path $LicenseFile) { try { $saved = Get-Content $LicenseFile -Raw | ConvertFrom-Json } catch { } }
  $answer = $null
  if ($saved -and $saved.license) {
    $answer = Invoke-Access 'update' 'x-tm-license' $saved.license
    if ($answer.ok) {
      if (-not $answer.download) { throw 'Setup got an unexpected answer from The Technomancer. Run this again in a minute.' }
      return $answer.download
    }
  }
  if ($env:TM_TICKET) {
    $answer = Invoke-Access 'redeem' 'x-tm-ticket' $env:TM_TICKET
    if ($answer.ok) {
      if (-not $answer.download) { throw 'Setup got an unexpected answer from The Technomancer. Run this again in a minute.' }
      New-Item -ItemType Directory -Force (Split-Path $LicenseFile) | Out-Null
      @{ license = $answer.license; ref = $answer.ref } | ConvertTo-Json -Compress | Set-Content -Path $LicenseFile -Encoding Ascii
      return $answer.download
    }
  }
  if ($answer) { throw $answer.message }
  return $null
}

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
if ($env:ASSISTANT_STARTER_DIR) {
  # The automated test installs the code it just checked out.
  if (Test-Path $Starter) { Remove-Item $Starter -Recurse -Force }
  New-Item -ItemType Directory -Force $Starter | Out-Null
  Get-ChildItem $env:ASSISTANT_STARTER_DIR -Force | Where-Object { $_.Name -ne '.git' } | Copy-Item -Destination $Starter -Recurse -Force
} else {
  $paid = Get-PaidDownload
  if ($paid -and $paid -notmatch '^(https://|http://(127\.0\.0\.1|localhost)[:/])') { throw 'Setup got an unexpected answer from The Technomancer. Run this again in a minute.' }
  Remove-Item Env:TM_TICKET -ErrorAction SilentlyContinue
  $download = Join-Path $env:TEMP 'assistant-starter.zip'
  $unpacked = Join-Path $HOME '.technomancer-setup.new'
  try { Invoke-WebRequest $(if ($paid) { $paid } else { $Zip }) -OutFile $download -UseBasicParsing }
  catch {
    if ($paid) { throw 'The setup page could not be downloaded. Check your internet connection and run this again.' }
    throw "This setup needs an active plan. Sign in at $Access/get-started to download your setup file."
  }
  if (Test-Path $unpacked) { Remove-Item $unpacked -Recurse -Force }
  Expand-Archive $download -DestinationPath $unpacked
  $top = Get-ChildItem $unpacked -Directory | Select-Object -First 1
  if (-not $top -or -not (Test-Path (Join-Path $top.FullName 'install\wizard.py'))) { throw 'The setup page could not be put in place. Your current setup was kept.' }
  # The working copy is set aside, and put back if the new one cannot take its place.
  $previous = $null
  if (Test-Path $Starter) {
    $previous = "$Starter.old"
    if (Test-Path $previous) { Remove-Item $previous -Recurse -Force }
    Move-Item $Starter $previous
  }
  try { Move-Item $top.FullName $Starter }
  catch {
    if (Test-Path $Starter) { Remove-Item $Starter -Recurse -Force }
    if ($previous) { Move-Item $previous $Starter }
    throw 'The setup page could not be put in place. Your current setup was kept.'
  }
  if ($previous) { Remove-Item $previous -Recurse -Force -ErrorAction SilentlyContinue }
  Remove-Item $download, $unpacked -Recurse -Force -ErrorAction SilentlyContinue
}
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
