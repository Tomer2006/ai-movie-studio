# Smoke-test: custom ffmpeg preview + concat (no cloud video APIs)
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $root

$exe = $null
$arg = @()
try {
  $c = Get-Command python -ErrorAction Stop
  $exe = $c.Source
} catch {}
if (-not $exe) {
  try {
    $c = Get-Command py -ErrorAction Stop
    $exe = $c.Source
    $arg = @("-3")
  } catch {}
}
if (-not $exe) {
  Write-Error "Python not found on PATH. Install Python 3.11+ and retry."
}

& $exe @arg -m pip install -e . -q
$env:VIDEO_PROVIDER = "custom"
& $exe @arg -m studio init-examples --force
& $exe @arg -m studio plan
& $exe @arg -m studio render-all
& $exe @arg -m studio assemble -o dist/pilot.mp4
Write-Host "OK: dist/pilot.mp4"
