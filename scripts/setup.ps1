<#
.SYNOPSIS
    SIH KWS - one-shot developer setup for Windows (PowerShell).

.DESCRIPTION
    Creates .venv in the repository root and installs from requirements*.txt.
    Never touches anything outside the repository. Safe to re-run.

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File scripts\setup.ps1
    powershell -ExecutionPolicy Bypass -File scripts\setup.ps1 -Dev
    powershell -ExecutionPolicy Bypass -File scripts\setup.ps1 -Dev -Server
#>
[CmdletBinding()]
param(
    [switch]$Dev,
    [switch]$Server
)

$ErrorActionPreference = 'Stop'

$RepoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $RepoRoot

Write-Host "=============================================================="
Write-Host "SIH KWS setup"
Write-Host "repository: $RepoRoot"
Write-Host "=============================================================="

# --- 1. pick a Python -------------------------------------------------------
# TensorFlow publishes no wheels for 3.14, so 3.10-3.13 only.
$py = $null
$candidates = @()
foreach ($v in '3.13', '3.12', '3.11', '3.10') {
    $candidates += ,@('py', @("-$v", '--version'), 'py', @("-$v"))
}
foreach ($c in $candidates) {
    if (Get-Command $c[0] -ErrorAction SilentlyContinue) {
        try {
            $null = & $c[0] $c[1] 2>$null
            if ($LASTEXITCODE -eq 0) { $py = @($c[2]) + $c[3]; break }
        } catch { }
    }
}
if (-not $py) {
    foreach ($name in 'python', 'python3') {
        $cmd = Get-Command $name -ErrorAction SilentlyContinue
        if ($cmd) {
            $ver = & $cmd.Source -c "import sys; print('%d.%d' % sys.version_info[:2])" 2>$null
            if ($ver -in @('3.10', '3.11', '3.12', '3.13')) { $py = @($cmd.Source); break }
        }
    }
}
if (-not $py) {
    Write-Host "ERROR: need Python 3.10-3.13 on PATH (TensorFlow has no 3.14 wheels)." -ForegroundColor Red
    Write-Host "See ENVIRONMENT_SETUP.md."
    exit 1
}
$pyVersion = & $py[0] $py[1..($py.Count-1)] --version 2>&1
Write-Host "[1/5] Python: $($py -join ' ')  ($pyVersion)"

# --- 2. virtual environment -------------------------------------------------
if (-not (Test-Path '.venv')) {
    Write-Host "[2/5] creating .venv"
    & $py[0] $py[1..($py.Count-1)] -m venv .venv
} else {
    Write-Host "[2/5] .venv already exists - reusing"
}
$VenvPy = Join-Path $RepoRoot '.venv\Scripts\python.exe'
if (-not (Test-Path $VenvPy)) { Write-Host "ERROR: venv creation failed" -ForegroundColor Red; exit 1 }

# --- 3. dependencies --------------------------------------------------------
Write-Host "[3/5] upgrading pip"
& $VenvPy -m pip install --quiet --upgrade pip

Write-Host "[3/5] installing requirements.txt (this pulls TensorFlow; be patient)"
& $VenvPy -m pip install -r requirements.txt
if ($LASTEXITCODE -ne 0) { Write-Host "pip install failed" -ForegroundColor Red; exit 1 }

if ($Dev) {
    Write-Host "[3/5] installing requirements-dev.txt"
    & $VenvPy -m pip install -r requirements-dev.txt
}
if ($Server) {
    Write-Host "[3/5] installing requirements-server.txt"
    & $VenvPy -m pip install -r requirements-server.txt
}

# --- 4. local config --------------------------------------------------------
if (-not (Test-Path '.env')) {
    Copy-Item '.env.example' '.env'
    Write-Host "[4/5] created .env from .env.example (git-ignored; edit for this machine)"
} else {
    Write-Host "[4/5] .env already exists - left untouched"
}

# --- 5. verify --------------------------------------------------------------
Write-Host "[5/5] verifying"
& $VenvPy scripts\verify_setup.py
$rc = $LASTEXITCODE

Write-Host ""
Write-Host "--------------------------------------------------------------"
Write-Host "Activate the environment with:"
Write-Host "    .\.venv\Scripts\Activate.ps1"
Write-Host ""
Write-Host "Then read CURRENT_HANDOFF.md - it names the exact next task."
Write-Host "--------------------------------------------------------------"
exit $rc
