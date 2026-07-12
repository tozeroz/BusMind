$ErrorActionPreference = 'Stop'

$repoRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$backendRoot = Join-Path $repoRoot 'backend'

if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    throw 'python command not found. Install Python first.'
}

Set-Location $backendRoot
Write-Host 'Starting backend on http://127.0.0.1:8000 ...'
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
